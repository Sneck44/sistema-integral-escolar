import os, hashlib
from datetime import date, datetime
from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint

DBURL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('POSTGRES_PRISMA_URL')
if DBURL and DBURL.startswith('postgres://'): DBURL='postgresql+psycopg://'+DBURL[len('postgres://'):]
elif DBURL and DBURL.startswith('postgresql://') and '+psycopg' not in DBURL: DBURL='postgresql+psycopg://'+DBURL[len('postgresql://'):]

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']=DBURL or 'sqlite:////tmp/escolar_demo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.secret_key=os.getenv('SECRET_KEY') or hashlib.sha256(('school:'+str(DBURL)).encode()).hexdigest()
db=SQLAlchemy(app)

FIELDS=['Lenguajes','Saberes y Pensamiento Científico','Ética, Naturaleza y Sociedades','De lo Humano y lo Comunitario']
TRIMS=['PRIMER TRIMESTRE','SEGUNDO TRIMESTRE','TERCER TRIMESTRE']

class User(db.Model):
 id=db.Column(db.Integer,primary_key=True); username=db.Column(db.String(80),unique=True,nullable=False); password=db.Column(db.String(255),nullable=False)
class Config(db.Model):
 id=db.Column(db.Integer,primary_key=True); school=db.Column(db.String(180),default='Telesecundaria Benito Juárez'); cct=db.Column(db.String(30),default=''); cycle=db.Column(db.String(30),default='2026–2027'); grade=db.Column(db.String(20),default='1.º'); group=db.Column(db.String(20),default='A')
class Student(db.Model):
 id=db.Column(db.Integer,primary_key=True); list_no=db.Column(db.Integer); paternal=db.Column(db.String(80),nullable=False); maternal=db.Column(db.String(80),default=''); names=db.Column(db.String(120),nullable=False); status=db.Column(db.String(20),default='ACTIVO'); tutor=db.Column(db.String(150),default=''); phone=db.Column(db.String(50),default='')
 @property
 def full_name(self): return f'{self.paternal} {self.maternal} {self.names}'.replace('  ',' ')
class Subject(db.Model):
 id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120),nullable=False); field=db.Column(db.String(120),nullable=False)
class Activity(db.Model):
 id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(160),nullable=False); subject_id=db.Column(db.Integer,db.ForeignKey('subject.id'),nullable=False); trimester=db.Column(db.String(40),nullable=False); activity_date=db.Column(db.Date,default=date.today); max_score=db.Column(db.Float,default=10); subject=db.relationship('Subject')
class Grade(db.Model):
 id=db.Column(db.Integer,primary_key=True); student_id=db.Column(db.Integer,db.ForeignKey('student.id')); activity_id=db.Column(db.Integer,db.ForeignKey('activity.id')); score=db.Column(db.Float); code=db.Column(db.String(10),default=''); __table_args__=(UniqueConstraint('student_id','activity_id'),)
class Attendance(db.Model):
 id=db.Column(db.Integer,primary_key=True); day=db.Column(db.Date,nullable=False); student_id=db.Column(db.Integer,db.ForeignKey('student.id')); state=db.Column(db.String(20),default='PRESENTE'); notes=db.Column(db.String(250),default=''); __table_args__=(UniqueConstraint('day','student_id'),)
class Incident(db.Model):
 id=db.Column(db.Integer,primary_key=True); day=db.Column(db.Date,default=date.today); student_id=db.Column(db.Integer,db.ForeignKey('student.id')); category=db.Column(db.String(80),default='Convivencia'); description=db.Column(db.Text,nullable=False); action=db.Column(db.Text,default=''); status=db.Column(db.String(30),default='ABIERTA'); student=db.relationship('Student')

def cfg():
 c=Config.query.first()
 if not c: c=Config(); db.session.add(c); db.session.commit()
 return c

def avg_student(sid):
 vals=[]
 for g in Grade.query.filter_by(student_id=sid).all():
  a=db.session.get(Activity,g.activity_id)
  if g.score is not None and a and a.max_score: vals.append(g.score/a.max_score*10)
 return round(sum(vals)/len(vals),2) if vals else None

def auth(): return session.get('uid')

def require():
 if not auth(): return redirect(url_for('login'))

def page(title,body):
 c=cfg(); nav=''
 if auth(): nav='''<nav><a href="/">Inicio</a><a href="/students">Alumnos</a><a href="/subjects">Asignaturas</a><a href="/activities">Actividades</a><a href="/attendance">Asistencia</a><a href="/incidents">Convivencia</a><a href="/config">Configuración</a><a href="/logout">Salir</a></nav>'''
 tpl='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}}</title><style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f4f7fb;color:#172033}header{background:#132a46;color:white;padding:18px 5vw}header h2{margin:0}nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}nav a{color:white;text-decoration:none;background:#ffffff18;padding:8px 10px;border-radius:8px}.wrap{max-width:1200px;margin:auto;padding:24px}.card{background:white;border-radius:14px;padding:18px;margin-bottom:18px;box-shadow:0 4px 18px #0000000b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.kpi{font-size:30px;font-weight:800}input,select,textarea,button{width:100%;padding:10px;border:1px solid #ccd4df;border-radius:8px;font:inherit}button{background:#1463d6;color:white;border:0;font-weight:700;cursor:pointer}label{font-size:13px;font-weight:700}table{width:100%;border-collapse:collapse;min-width:650px}th,td{padding:10px;border-bottom:1px solid #e8edf4;text-align:left}.scroll{overflow:auto}.alert{padding:10px;border-radius:8px;background:#fff1c7;margin-bottom:12px}.danger{background:#ffe1e1}.muted{color:#657085;font-size:13px}h1{margin-top:0}@media(max-width:650px){.wrap{padding:14px}header{padding:15px}table{font-size:13px}}</style></head><body><header><h2>{{c.school}}</h2><div>{{c.cct}} · Ciclo {{c.cycle}}</div>'''+nav+'''</header><main class="wrap">{% with ms=get_flashed_messages() %}{% for m in ms %}<div class="alert">{{m}}</div>{% endfor %}{% endwith %}'''+body+'''</main></body></html>'''
 return render_template_string(tpl,title=title,c=c)

@app.before_request
def boot():
 db.create_all(); cfg()
 if not DBURL and os.getenv('VERCEL') and request.endpoint not in ('db_missing',): return redirect('/db-missing')
@app.route('/db-missing')
def db_missing(): return page('Base de datos','<div class="card danger"><h1>Neon aún no está enlazado</h1><p>Vercel no entregó DATABASE_URL/POSTGRES_URL a este despliegue. No se guardarán datos hasta conectarla.</p></div>')
@app.route('/setup',methods=['GET','POST'])
def setup():
 if User.query.first(): return redirect('/login')
 if request.method=='POST':
  u=request.form['user'].strip(); p=request.form['password']
  if len(p)<10: flash('Usa una contraseña de al menos 10 caracteres.')
  else: db.session.add(User(username=u,password=generate_password_hash(p))); db.session.commit(); flash('Administrador creado.'); return redirect('/login')
 return page('Configuración inicial','''<div class="card" style="max-width:520px;margin:auto"><h1>Crear administrador</h1><form method="post"><label>Usuario<input name="user" required></label><br><br><label>Contraseña<input name="password" type="password" minlength="10" required></label><br><br><button>Crear cuenta</button></form></div>''')
@app.route('/login',methods=['GET','POST'])
def login():
 if not User.query.first(): return redirect('/setup')
 if request.method=='POST':
  u=User.query.filter_by(username=request.form['user']).first()
  if u and check_password_hash(u.password,request.form['password']): session['uid']=u.id; return redirect('/')
  flash('Usuario o contraseña incorrectos.')
 return page('Acceso','''<div class="card" style="max-width:460px;margin:auto"><h1>Acceso</h1><form method="post"><label>Usuario<input name="user" required></label><br><br><label>Contraseña<input name="password" type="password" required></label><br><br><button>Entrar</button></form></div>''')
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/')
def dashboard():
 r=require()
 if r:return r
 students=Student.query.filter_by(status='ACTIVO').all(); av=[avg_student(s.id) for s in students]; av=[x for x in av if x is not None]
 total=Attendance.query.count(); present=Attendance.query.filter(Attendance.state.in_(['PRESENTE','RETARDO'])).count(); att=round(present*100/total,1) if total else 0
 body=f'''<h1>Panel de control</h1><div class="grid"><div class="card"><div class="muted">Alumnos activos</div><div class="kpi">{len(students)}</div></div><div class="card"><div class="muted">Promedio general</div><div class="kpi">{round(sum(av)/len(av),2) if av else '—'}</div></div><div class="card"><div class="muted">Asistencia</div><div class="kpi">{att}%</div></div><div class="card"><div class="muted">Incidencias abiertas</div><div class="kpi">{Incident.query.filter_by(status='ABIERTA').count()}</div></div></div><div class="card"><h2>Sistema listo</h2><p>Registra alumnos, actividades, calificaciones, asistencia e incidencias desde el menú.</p></div>'''
 return page('Inicio',body)
@app.route('/students',methods=['GET','POST'])
def students():
 r=require()
 if r:return r
 if request.method=='POST':
  db.session.add(Student(list_no=request.form.get('list_no',type=int),paternal=request.form['paternal'].strip(),maternal=request.form.get('maternal','').strip(),names=request.form['names'].strip(),tutor=request.form.get('tutor',''),phone=request.form.get('phone',''))); db.session.commit(); flash('Alumno guardado.'); return redirect('/students')
 rows=''.join(f'<tr><td>{s.list_no or ""}</td><td>{s.full_name}</td><td>{avg_student(s.id) if avg_student(s.id) is not None else "—"}</td><td>{s.tutor}</td></tr>' for s in Student.query.order_by(Student.list_no,Student.paternal).all())
 body='''<h1>Alumnos</h1><div class="card"><form method="post" class="grid"><label>No. lista<input name="list_no" type="number"></label><label>Apellido paterno<input name="paternal" required></label><label>Apellido materno<input name="maternal"></label><label>Nombre(s)<input name="names" required></label><label>Tutor<input name="tutor"></label><label>Teléfono<input name="phone"></label><div><button>Agregar alumno</button></div></form></div><div class="card scroll"><table><tr><th>No.</th><th>Alumno</th><th>Promedio</th><th>Tutor</th></tr>'''+rows+'</table></div>'
 return page('Alumnos',body)
@app.route('/subjects',methods=['GET','POST'])
def subjects():
 r=require()
 if r:return r
 if request.method=='POST': db.session.add(Subject(name=request.form['name'],field=request.form['field'])); db.session.commit(); flash('Asignatura agregada.'); return redirect('/subjects')
 opts=''.join(f'<option>{x}</option>' for x in FIELDS); rows=''.join(f'<tr><td>{s.name}</td><td>{s.field}</td></tr>' for s in Subject.query.order_by(Subject.name).all())
 return page('Asignaturas',f'''<h1>Asignaturas</h1><div class="card"><form method="post" class="grid"><label>Asignatura<input name="name" required></label><label>Campo formativo<select name="field">{opts}</select></label><div><button>Agregar</button></div></form></div><div class="card scroll"><table><tr><th>Asignatura</th><th>Campo</th></tr>{rows}</table></div>''')
@app.route('/activities',methods=['GET','POST'])
def activities():
 r=require()
 if r:return r
 subs=Subject.query.all()
 if request.method=='POST': db.session.add(Activity(name=request.form['name'],subject_id=int(request.form['subject_id']),trimester=request.form['trimester'],activity_date=datetime.strptime(request.form['day'],'%Y-%m-%d').date(),max_score=float(request.form.get('max_score') or 10))); db.session.commit(); flash('Actividad creada.'); return redirect('/activities')
 so=''.join(f'<option value="{s.id}">{s.name}</option>' for s in subs); to=''.join(f'<option>{t}</option>' for t in TRIMS); rows=''.join(f'<tr><td>{a.activity_date}</td><td>{a.name}</td><td>{a.subject.name}</td><td>{a.trimester}</td><td><a href="/grades/{a.id}">Calificar</a></td></tr>' for a in Activity.query.order_by(Activity.activity_date.desc()).all())
 return page('Actividades',f'''<h1>Actividades</h1><div class="card"><form method="post" class="grid"><label>Fecha<input type="date" name="day" value="{date.today()}" required></label><label>Nombre<input name="name" required></label><label>Asignatura<select name="subject_id">{so}</select></label><label>Trimestre<select name="trimester">{to}</select></label><label>Puntaje máximo<input name="max_score" type="number" step=".01" value="10"></label><div><button>Crear</button></div></form></div><div class="card scroll"><table><tr><th>Fecha</th><th>Actividad</th><th>Asignatura</th><th>Trimestre</th><th></th></tr>{rows}</table></div>''')
@app.route('/grades/<int:aid>',methods=['GET','POST'])
def grades(aid):
 r=require()
 if r:return r
 a=db.session.get(Activity,aid)
 students=Student.query.filter_by(status='ACTIVO').order_by(Student.list_no).all()
 if request.method=='POST':
  for s in students:
   raw=request.form.get(f'g{s.id}','').strip(); g=Grade.query.filter_by(student_id=s.id,activity_id=aid).first() or Grade(student_id=s.id,activity_id=aid)
   if raw.upper() in ('NP','NE','J','P'): g.score=None; g.code=raw.upper()
   else:
    try:g.score=float(raw);g.code=''
    except:g.score=None;g.code=''
   db.session.add(g)
  db.session.commit(); flash('Calificaciones guardadas.'); return redirect(f'/grades/{aid}')
 rows=''
 for s in students:
  g=Grade.query.filter_by(student_id=s.id,activity_id=aid).first(); val=(g.code if g and g.code else (g.score if g and g.score is not None else ''))
  rows+=f'<tr><td>{s.list_no or ""}</td><td>{s.full_name}</td><td><input name="g{s.id}" value="{val}"></td></tr>'
 return page('Calificaciones',f'''<h1>{a.name}</h1><p>{a.subject.name} · máximo {a.max_score}</p><form method="post" class="card scroll"><table><tr><th>No.</th><th>Alumno</th><th>Calificación / NP / NE / J / P</th></tr>{rows}</table><br><button>Guardar calificaciones</button></form>''')
@app.route('/attendance',methods=['GET','POST'])
def attendance():
 r=require()
 if r:return r
 day=datetime.strptime(request.values.get('day') or str(date.today()),'%Y-%m-%d').date(); students=Student.query.filter_by(status='ACTIVO').order_by(Student.list_no).all()
 if request.method=='POST':
  for s in students:
   x=Attendance.query.filter_by(day=day,student_id=s.id).first() or Attendance(day=day,student_id=s.id)
   x.state=request.form.get(f's{s.id}','PRESENTE'); x.notes=request.form.get(f'n{s.id}',''); db.session.add(x)
  db.session.commit(); flash('Asistencia guardada.'); return redirect('/attendance?day='+str(day))
 rows=''
 for s in students:
  x=Attendance.query.filter_by(day=day,student_id=s.id).first(); st=x.state if x else 'PRESENTE'; ops=''.join(f'<option {"selected" if st==z else ""}>{z}</option>' for z in ['PRESENTE','AUSENTE','RETARDO','JUSTIFICADA']); rows+=f'<tr><td>{s.list_no or ""}</td><td>{s.full_name}</td><td><select name="s{s.id}">{ops}</select></td><td><input name="n{s.id}" value="{x.notes if x else ""}"></td></tr>'
 return page('Asistencia',f'''<h1>Asistencia</h1><form method="get" class="card"><label>Fecha<input type="date" name="day" value="{day}"></label><br><br><button>Cargar fecha</button></form><form method="post" class="card scroll"><input type="hidden" name="day" value="{day}"><table><tr><th>No.</th><th>Alumno</th><th>Estado</th><th>Notas</th></tr>{rows}</table><br><button>Guardar asistencia</button></form>''')
@app.route('/incidents',methods=['GET','POST'])
def incidents():
 r=require()
 if r:return r
 students=Student.query.filter_by(status='ACTIVO').order_by(Student.list_no).all()
 if request.method=='POST': db.session.add(Incident(day=datetime.strptime(request.form['day'],'%Y-%m-%d').date(),student_id=int(request.form['student_id']),category=request.form['category'],description=request.form['description'],action=request.form.get('action',''),status=request.form.get('status','ABIERTA'))); db.session.commit(); flash('Incidencia registrada.'); return redirect('/incidents')
 so=''.join(f'<option value="{s.id}">{s.full_name}</option>' for s in students); rows=''.join(f'<tr><td>{i.day}</td><td>{i.student.full_name}</td><td>{i.category}</td><td>{i.description}</td><td>{i.status}</td></tr>' for i in Incident.query.order_by(Incident.day.desc()).all())
 return page('Convivencia',f'''<h1>Convivencia e incidencias</h1><div class="card"><p class="muted">Registra hechos objetivos y seguimiento; el sistema no asigna sanciones automáticamente.</p><form method="post" class="grid"><label>Fecha<input type="date" name="day" value="{date.today()}" required></label><label>Alumno<select name="student_id">{so}</select></label><label>Categoría<input name="category" value="Convivencia"></label><label class="wide">Descripción objetiva<textarea name="description" required></textarea></label><label>Intervención / acuerdos<textarea name="action"></textarea></label><label>Estado<select name="status"><option>ABIERTA</option><option>EN SEGUIMIENTO</option><option>CERRADA</option></select></label><div><button>Registrar</button></div></form></div><div class="card scroll"><table><tr><th>Fecha</th><th>Alumno</th><th>Categoría</th><th>Descripción</th><th>Estado</th></tr>{rows}</table></div>''')
@app.route('/config',methods=['GET','POST'])
def config():
 r=require()
 if r:return r
 c=cfg()
 if request.method=='POST': c.school=request.form['school'];c.cct=request.form.get('cct','');c.cycle=request.form['cycle'];c.grade=request.form.get('grade','');c.group=request.form.get('group','');db.session.commit();flash('Configuración guardada.');return redirect('/config')
 return page('Configuración',f'''<h1>Configuración</h1><form method="post" class="card grid"><label>Escuela<input name="school" value="{c.school}"></label><label>CCT<input name="cct" value="{c.cct}"></label><label>Ciclo<input name="cycle" value="{c.cycle}"></label><label>Grado<input name="grade" value="{c.grade}"></label><label>Grupo<input name="group" value="{c.group}"></label><div><button>Guardar</button></div></form>''')

with app.app_context():
 try: db.create_all(); cfg()
 except Exception as e: print('DB init pending:',e)

if __name__=='__main__': app.run(debug=True)
