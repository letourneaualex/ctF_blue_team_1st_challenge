import os
import psycopg2
from flask import (Flask, request, session, redirect, render_template,
                   Response, abort, jsonify)
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.debug = config.DEBUG


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    return psycopg2.connect(config.DATABASE_URL)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html',
                           username=session.get('username'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        try:
            conn = get_db()
            cur = conn.cursor()
            # VULNERABLE: SQL injection via string formatting
            query = (f"SELECT id, username FROM users "
                     f"WHERE username='{username}' AND password='{password}'")
            cur.execute(query)
            user = cur.fetchone()
            conn.close()
        except Exception:
            user = None

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect('/')
        error = 'Invalid credentials'
    return render_template('login.html', error=error)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        email    = request.form.get('email', '')
        password = request.form.get('password', '')
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password)
            )
            conn.commit()
            conn.close()
            return redirect('/login')
        except Exception as e:
            error = 'Registration failed'
    return render_template('register.html', error=error)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    # VULNERABLE: no ownership check — IDOR
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, bio FROM users WHERE id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        conn.close()
    except Exception:
        abort(500)

    if not row:
        abort(404)

    user = {'id': row[0], 'username': row[1], 'email': row[2], 'bio': row[3]}
    return render_template('profile.html', user=user,
                           current_user_id=session.get('user_id'))


@app.route('/profile/edit', methods=['GET', 'POST'])
def profile_edit():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        bio = request.form.get('bio', '')
        try:
            conn = get_db()
            cur = conn.cursor()
            # VULNERABLE: stores raw HTML — stored XSS
            cur.execute(
                "UPDATE users SET bio = %s WHERE id = %s",
                (bio, session['user_id'])
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        return redirect(f'/profile/{session["user_id"]}')
    return render_template('profile_edit.html')


@app.route('/search')
def search():
    q = request.args.get('q', '')
    results = []
    if q:
        try:
            conn = get_db()
            cur = conn.cursor()
            # VULNERABLE: SQL injection (UNION extract) via string formatting
            query = (f"SELECT title, content FROM posts "
                     f"WHERE title LIKE '%{q}%' OR content LIKE '%{q}%'")
            cur.execute(query)
            results = cur.fetchall()
            conn.close()
        except Exception:
            results = []
    # VULNERABLE: query reflected unsanitised — reflected XSS (handled in template)
    return render_template('search.html', query=q, results=results)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        f = request.files.get('file')
        if not f or f.filename == '':
            return 'No file selected', 400
        # VULNERABLE: no file-type validation — accepts any extension
        filename = f.filename
        f.save(f'/app/uploads/{filename}')
        return redirect('/')
    return render_template('upload.html')


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    # VULNERABLE: no path sanitisation — path traversal
    # e.g. /uploads/../../etc/passwd resolves to /etc/passwd
    filepath = '/app/uploads/' + filename
    try:
        with open(filepath, 'rb') as fh:
            data = fh.read()
        return Response(data, mimetype='application/octet-stream')
    except (OSError, IsADirectoryError):
        abort(404)


@app.route('/account/password', methods=['GET', 'POST'])
def account_password():
    if 'user_id' not in session:
        return redirect('/login')
    error = None
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw     = request.form.get('new_password', '')
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT password FROM users WHERE id = %s",
                (session['user_id'],)
            )
            row = cur.fetchone()
            if row and row[0] == current_pw:
                cur.execute(
                    "UPDATE users SET password = %s WHERE id = %s",
                    (new_pw, session['user_id'])
                )
                conn.commit()
                conn.close()
                return redirect('/')
            conn.close()
            error = 'Current password is incorrect'
        except Exception:
            error = 'Error updating password'
    return render_template('account.html', error=error)


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/status')
def api_status():
    return jsonify({'status': 'ok', 'version': '2.0'})


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/force-error-for-debug-check')
def force_error():
    # VULNERABLE: with DEBUG=True this returns the Werkzeug interactive debugger
    raise RuntimeError("Intentional error — debug mode check")


@app.route('/<path:arbitrary_path>')
def filesystem_catchall(arbitrary_path):
    # VULNERABLE: catch-all that enables path traversal.
    # Werkzeug normalises /uploads/../../etc/passwd → /etc/passwd before routing,
    # so this route intercepts the resolved path and serves the file directly.
    filepath = '/' + arbitrary_path
    if os.path.isfile(filepath):
        try:
            with open(filepath, 'rb') as fh:
                return Response(fh.read(), mimetype='application/octet-stream')
        except OSError:
            pass
    abort(404)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=config.DEBUG)
