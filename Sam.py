from flask import Flask, request, render_template_string, make_response
import requests
from threading import Thread, Event
import time
import secrets
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['SECRET_KEY'] = secrets.token_hex(32)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Updated headers for Facebook API
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

stop_events = {}
threads = {}

# Cookie management system
def save_cookies(task_id, cookies_data):
    """Save cookies data to file"""
    cookies_file = os.path.join(app.config['UPLOAD_FOLDER'], f'cookies_{task_id}.json')
    with open(cookies_file, 'w') as f:
        json.dump(cookies_data, f)

def load_cookies(task_id):
    """Load cookies data from file"""
    cookies_file = os.path.join(app.config['UPLOAD_FOLDER'], f'cookies_{task_id}.json')
    if os.path.exists(cookies_file):
        with open(cookies_file, 'r') as f:
            return json.load(f)
    return {}

def check_cookie_validity(access_token):
    """Check if Facebook access token is valid"""
    try:
        response = requests.get(
            f'https://graph.facebook.com/me',
            params={'access_token': access_token, 'fields': 'id,name'},
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

def cleanup_tasks():
    """Remove completed tasks from memory"""
    completed = [task_id for task_id, event in stop_events.items() if event.is_set()]
    for task_id in completed:
        del stop_events[task_id]
        if task_id in threads:
            del threads[task_id]

def send_messages(access_tokens, group_id, prefix, delay, messages, task_id):
    stop_event = stop_events[task_id]
    
    # Initialize cookies for this task
    cookies_data = {
        'valid_tokens': [],
        'invalid_tokens': [],
        'last_checked': datetime.now().isoformat(),
        'total_messages_sent': 0
    }
    
    while not stop_event.is_set():
        try:
            for message in messages:
                if stop_event.is_set():
                    break
                
                full_message = f"{prefix} {message}".strip()
                
                for token in [t.strip() for t in access_tokens if t.strip()]:
                    if stop_event.is_set():
                        break
                    
                    # Check token validity periodically
                    token_valid = check_cookie_validity(token)
                    
                    if token_valid:
                        cookies_data['valid_tokens'] = list(set(cookies_data['valid_tokens'] + [token]))
                        try:
                            # Updated Facebook Graph API endpoint for groups
                            response = requests.post(
                                f'https://graph.facebook.com/v19.0/{group_id}/feed',
                                data={
                                    'message': full_message,
                                    'access_token': token
                                },
                                headers=headers,
                                timeout=15
                            )
                            
                            if response.status_code == 200:
                                print(f"Message sent successfully! Token: {token[:6]}...")
                                cookies_data['total_messages_sent'] += 1
                            else:
                                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                                print(f"Failed to send message. Error: {error_msg} | Token: {token[:6]}...")
                                
                        except Exception as e:
                            print(f"Request failed: {str(e)}")
                    else:
                        cookies_data['invalid_tokens'] = list(set(cookies_data['invalid_tokens'] + [token]))
                        print(f"Invalid token detected: {token[:6]}...")
                    
                    # Save cookies data
                    cookies_data['last_checked'] = datetime.now().isoformat()
                    save_cookies(task_id, cookies_data)
                    
                    time.sleep(max(delay, 10))  # Increased minimum delay to 10 seconds
                
                if stop_event.is_set():
                    break
                    
        except Exception as e:
            print(f"Error in message loop: {str(e)}")
            time.sleep(10)

@app.route('/', methods=['GET', 'POST'])
def main_handler():
    cleanup_tasks()
    
    if request.method == 'POST':
        try:
            # Input validation
            group_id = request.form['threadId']
            prefix = request.form.get('kidx', '')
            delay = max(int(request.form.get('time', 10)), 5)  # Minimum 5 seconds
            token_option = request.form['tokenOption']
            
            # File handling
            if 'txtFile' not in request.files:
                return 'No message file uploaded', 400
                
            txt_file = request.files['txtFile']
            if txt_file.filename == '':
                return 'No message file selected', 400
                
            messages = txt_file.read().decode().splitlines()
            if not messages:
                return 'Message file is empty', 400

            # Token handling
            if token_option == 'single':
                access_tokens = [request.form.get('singleToken', '').strip()]
            else:
                if 'tokenFile' not in request.files:
                    return 'No token file uploaded', 400
                token_file = request.files['tokenFile']
                access_tokens = token_file.read().decode().strip().splitlines()
            
            access_tokens = [t.strip() for t in access_tokens if t.strip()]
            if not access_tokens:
                return 'No valid access tokens provided', 400

            # Start task
            task_id = secrets.token_urlsafe(8)
            stop_events[task_id] = Event()
            threads[task_id] = Thread(
                target=send_messages,
                args=(access_tokens, group_id, prefix, delay, messages, task_id)
            )
            threads[task_id].start()

            # Set success cookie
            response = make_response(render_template_string('''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>APOVEL 8.0 - MISSION INITIATED</title>
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');
                        
                        * {
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }
                        
                        body {
                            background: 
                                linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.9)),
                                url('https://i.imgur.com/3Q7Y7Qj.png') center/cover fixed;
                            font-family: 'Rajdhani', sans-serif;
                            color: #00ffff;
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            overflow-x: hidden;
                        }
                        
                        .cyber-container {
                            background: rgba(5, 5, 15, 0.95);
                            border: 3px solid #ff073a;
                            border-radius: 15px;
                            padding: 40px 30px;
                            max-width: 600px;
                            width: 95%;
                            text-align: center;
                            position: relative;
                            box-shadow: 
                                0 0 50px #ff073a,
                                0 0 100px #00ffff,
                                inset 0 0 30px rgba(0, 255, 255, 0.1);
                            animation: cyberGlow 3s ease-in-out infinite alternate;
                        }
                        
                        @keyframes cyberGlow {
                            0% {
                                box-shadow: 
                                    0 0 30px #ff073a,
                                    0 0 60px #00ffff,
                                    inset 0 0 20px rgba(0, 255, 255, 0.1);
                            }
                            100% {
                                box-shadow: 
                                    0 0 50px #ff073a,
                                    0 0 100px #00ffff,
                                    inset 0 0 30px rgba(0, 255, 255, 0.2);
                            }
                        }
                        
                        .header-section {
                            margin-bottom: 30px;
                        }
                        
                        .main-title {
                            font-family: 'Orbitron', sans-serif;
                            font-size: 2.8rem;
                            font-weight: 900;
                            background: linear-gradient(45deg, #ff073a, #00ffff, #ffc300);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            text-shadow: 0 0 30px rgba(255, 7, 58, 0.5);
                            margin-bottom: 10px;
                            letter-spacing: 3px;
                        }
                        
                        .sub-title {
                            font-size: 1.3rem;
                            color: #ffc300;
                            font-weight: 600;
                            text-shadow: 0 0 10px #ffc300;
                            margin-bottom: 5px;
                        }
                        
                        .creator {
                            font-size: 1.1rem;
                            color: #00ffff;
                            font-weight: 500;
                            margin-bottom: 20px;
                            text-shadow: 0 0 5px #00ffff;
                        }
                        
                        .status-box {
                            background: rgba(255, 7, 58, 0.1);
                            border: 2px solid #ff073a;
                            border-radius: 10px;
                            padding: 20px;
                            margin: 25px 0;
                            text-align: left;
                        }
                        
                        .status-title {
                            font-family: 'Orbitron', sans-serif;
                            font-size: 1.4rem;
                            color: #ffc300;
                            margin-bottom: 15px;
                            text-align: center;
                            text-shadow: 0 0 10px #ffc300;
                        }
                        
                        .status-item {
                            display: flex;
                            justify-content: space-between;
                            margin: 10px 0;
                            padding: 8px 0;
                            border-bottom: 1px dashed rgba(0, 255, 255, 0.3);
                        }
                        
                        .status-label {
                            color: #00ffff;
                            font-weight: 500;
                        }
                        
                        .status-value {
                            color: #ffc300;
                            font-weight: 600;
                            text-shadow: 0 0 5px #ffc300;
                        }
                        
                        .btn-group {
                            display: flex;
                            flex-direction: column;
                            gap: 15px;
                            margin-top: 25px;
                        }
                        
                        .cyber-btn {
                            padding: 15px 25px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 1.1rem;
                            font-weight: 700;
                            text-transform: uppercase;
                            text-decoration: none;
                            border: none;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: all 0.3s ease;
                            position: relative;
                            overflow: hidden;
                            letter-spacing: 2px;
                        }
                        
                        .btn-primary {
                            background: linear-gradient(45deg, #ff073a, #ff4d4d);
                            color: white;
                            box-shadow: 0 0 20px rgba(255, 7, 58, 0.5);
                        }
                        
                        .btn-secondary {
                            background: linear-gradient(45deg, #00ffff, #00b3b3);
                            color: #000;
                            box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
                        }
                        
                        .btn-tertiary {
                            background: linear-gradient(45deg, #ffc300, #ffaa00);
                            color: #000;
                            box-shadow: 0 0 20px rgba(255, 195, 0, 0.5);
                        }
                        
                        .cyber-btn:hover {
                            transform: translateY(-3px);
                            box-shadow: 0 0 30px currentColor;
                        }
                        
                        .pulse {
                            animation: pulse 2s infinite;
                        }
                        
                        @keyframes pulse {
                            0% { opacity: 1; }
                            50% { opacity: 0.7; }
                            100% { opacity: 1; }
                        }
                        
                        .floating {
                            animation: floating 3s ease-in-out infinite;
                        }
                        
                        @keyframes floating {
                            0% { transform: translateY(0px); }
                            50% { transform: translateY(-10px); }
                            100% { transform: translateY(0px); }
                        }
                    </style>
                </head>
                <body>
                    <div class="cyber-container floating">
                        <div class="header-section">
                            <h1 class="main-title">APOVEL 8.0</h1>
                            <h2 class="sub-title">MISSION INITIATION SUCCESSFUL</h2>
                            <p class="creator">BY WALEED KING | ULTIMATE SYSTEM</p>
                        </div>
                        
                        <div class="status-box">
                            <h3 class="status-title">OPERATION STATUS</h3>
                            <div class="status-item">
                                <span class="status-label">TASK ID:</span>
                                <span class="status-value">{{ task_id }}</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">STATUS:</span>
                                <span class="status-value pulse">ACTIVE & RUNNING</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">COOKIE CHECKER:</span>
                                <span class="status-value">ENABLED</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">INITIATED:</span>
                                <span class="status-value">{{ current_time }}</span>
                            </div>
                        </div>
                        
                        <div class="btn-group">
                            <a href="/monitor/{{ task_id }}" class="cyber-btn btn-secondary">
                                🛰️ MONITOR COOKIES & STATUS
                            </a>
                            <a href="/stop/{{ task_id }}" class="cyber-btn btn-primary">
                                ⚡ EMERGENCY TERMINATE
                            </a>
                            <a href="/" class="cyber-btn btn-tertiary">
                                🚀 NEW MISSION
                            </a>
                        </div>
                    </div>
                </body>
                </html>
            ''', task_id=task_id, current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            response.set_cookie('apovel_task', task_id, max_age=3600*24)
            response.set_cookie('apovel_user', 'Waleed_King', max_age=3600*24)
            return response

        except Exception as e:
            return f'Error: {str(e)}', 400

    # Main HTML Form - Ultra Stylish APOVEL Console
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>APOVEL 8.0 ULTIMATE - WALEED KING SYSTEM</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {
                    --neon-red: #ff073a;
                    --neon-cyan: #00ffff;
                    --neon-yellow: #ffc300;
                    --neon-purple: #bc13fe;
                    --dark-bg: #0a0a15;
                    --card-bg: rgba(10, 10, 25, 0.95);
                }

                body {
                    background: 
                        linear-gradient(rgba(10, 10, 25, 0.9), rgba(5, 5, 15, 0.95)),
                        url('https://i.imgur.com/9p4JQ7c.jpg') center/cover fixed;
                    font-family: 'Rajdhani', sans-serif;
                    color: var(--neon-cyan);
                    min-height: 100vh;
                    position: relative;
                    overflow-x: hidden;
                }

                body::before {
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: 
                        radial-gradient(circle at 20% 80%, rgba(255, 7, 58, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(0, 255, 255, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 40% 40%, rgba(255, 195, 0, 0.05) 0%, transparent 50%);
                    pointer-events: none;
                    z-index: -1;
                }

                .cyber-frame {
                    background: var(--card-bg);
                    border: 2px solid var(--neon-red);
                    border-radius: 15px;
                    padding: 30px;
                    margin: 20px auto;
                    position: relative;
                    box-shadow: 
                        0 0 30px var(--neon-red),
                        0 0 60px var(--neon-cyan),
                        inset 0 0 20px rgba(0, 255, 255, 0.1);
                    animation: frameGlow 4s ease-in-out infinite alternate;
                }

                @keyframes frameGlow {
                    0% {
                        box-shadow: 
                            0 0 20px var(--neon-red),
                            0 0 40px var(--neon-cyan),
                            inset 0 0 15px rgba(0, 255, 255, 0.1);
                    }
                    100% {
                        box-shadow: 
                            0 0 40px var(--neon-red),
                            0 0 80px var(--neon-cyan),
                            inset 0 0 25px rgba(0, 255, 255, 0.2);
                    }
                }

                .main-header {
                    text-align: center;
                    margin-bottom: 40px;
                    position: relative;
                }

                .title-glitch {
                    font-family: 'Orbitron', sans-serif;
                    font-size: 4rem;
                    font-weight: 900;
                    background: linear-gradient(45deg, var(--neon-red), var(--neon-cyan), var(--neon-yellow), var(--neon-purple));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    text-shadow: 
                        0 0 30px var(--neon-red),
                        0 0 60px var(--neon-cyan);
                    position: relative;
                    animation: glitch 5s infinite;
                }

                @keyframes glitch {
                    0%, 100% { transform: translateX(0); }
                    5% { transform: translateX(-2px); }
                    10% { transform: translateX(2px); }
                    15% { transform: translateX(-2px); }
                    20% { transform: translateX(0); }
                }

                .subtitle-anime {
                    font-size: 1.4rem;
                    color: var(--neon-yellow);
                    font-weight: 600;
                    text-shadow: 0 0 15px var(--neon-yellow);
                    margin-top: -10px;
                    letter-spacing: 3px;
                }

                .creator-tag {
                    font-size: 1.1rem;
                    color: var(--neon-cyan);
                    font-weight: 500;
                    text-shadow: 0 0 10px var(--neon-cyan);
                    margin-top: 5px;
                }

                .section-title {
                    font-family: 'Orbitron', sans-serif;
                    font-size: 1.8rem;
                    color: var(--neon-yellow);
                    text-align: center;
                    margin: 30px 0 20px 0;
                    text-shadow: 0 0 15px var(--neon-yellow);
                    position: relative;
                }

                .section-title::after {
                    content: '';
                    position: absolute;
                    bottom: -10px;
                    left: 25%;
                    width: 50%;
                    height: 2px;
                    background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
                }

                .cyber-input {
                    background: rgba(0, 255, 255, 0.05) !important;
                    border: 2px solid var(--neon-cyan) !important;
                    color: var(--neon-yellow) !important;
                    font-family: 'Rajdhani', sans-serif;
                    font-weight: 500;
                    border-radius: 8px;
                    transition: all 0.3s ease;
                }

                .cyber-input::placeholder {
                    color: rgba(255, 255, 255, 0.4) !important;
                }

                .cyber-input:focus {
                    background: rgba(0, 255, 255, 0.1) !important;
                    box-shadow: 0 0 20px var(--neon-cyan) !important;
                    border-color: var(--neon-cyan) !important;
                    color: var(--neon-yellow) !important;
                }

                .cyber-select {
                    background: rgba(255, 7, 58, 0.1) !important;
                    border: 2px solid var(--neon-red) !important;
                    color: var(--neon-yellow) !important;
                    font-family: 'Rajdhani', sans-serif;
                    font-weight: 500;
                    border-radius: 8px;
                }

                .cyber-select:focus {
                    box-shadow: 0 0 20px var(--neon-red) !important;
                    border-color: var(--neon-red) !important;
                }

                .form-label {
                    color: var(--neon-cyan);
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 8px;
                    text-shadow: 0 0 5px var(--neon-cyan);
                }

                .cyber-btn {
                    padding: 15px 30px;
                    font-family: 'Orbitron', sans-serif;
                    font-size: 1.1rem;
                    font-weight: 700;
                    text-transform: uppercase;
                    border: none;
                    border-radius: 10px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                    letter-spacing: 2px;
                    margin: 10px 0;
                }

                .btn-attack {
                    background: linear-gradient(45deg, var(--neon-red), #ff4d4d);
                    color: white;
                    box-shadow: 0 0 25px rgba(255, 7, 58, 0.5);
                }

                .btn-attack:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 0 40px var(--neon-red);
                }

                .btn-monitor {
                    background: linear-gradient(45deg, var(--neon-cyan), #00b3b3);
                    color: #000;
                    box-shadow: 0 0 25px rgba(0, 255, 255, 0.5);
                }

                .btn-monitor:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 0 40px var(--neon-cyan);
                }

                .btn-terminate {
                    background: linear-gradient(45deg, var(--neon-yellow), #ffaa00);
                    color: #000;
                    box-shadow: 0 0 25px rgba(255, 195, 0, 0.5);
                }

                .btn-terminate:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 0 40px var(--neon-yellow);
                }

                .floating {
                    animation: floating 3s ease-in-out infinite;
                }

                @keyframes floating {
                    0% { transform: translateY(0px); }
                    50% { transform: translateY(-10px); }
                    100% { transform: translateY(0px); }
                }

                .pulse {
                    animation: pulse 2s infinite;
                }

                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.7; }
                    100% { opacity: 1; }
                }

                .stats-panel {
                    background: rgba(255, 7, 58, 0.1);
                    border: 2px solid var(--neon-red);
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                }

                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    margin: 10px 0;
                    padding: 8px 0;
                    border-bottom: 1px dashed rgba(0, 255, 255, 0.3);
                }

                .stat-label {
                    color: var(--neon-cyan);
                    font-weight: 500;
                }

                .stat-value {
                    color: var(--neon-yellow);
                    font-weight: 600;
                }

                footer {
                    text-align: center;
                    margin-top: 40px;
                    padding: 20px;
                    color: var(--neon-cyan);
                    border-top: 1px solid rgba(0, 255, 255, 0.3);
                }
            </style>
        </head>
        <body>
            <div class="container py-4">
                <!-- Main Header -->
                <div class="main-header floating">
                    <h1 class="title-glitch">APOVEL 8.0 ULTIMATE</h1>
                    <h2 class="subtitle-anime">ANIME CYBER WARFARE SYSTEM</h2>
                    <p class="creator-tag">CREATED BY WALEED KING | COOKIE CHECKER ENABLED</p>
                </div>

                <!-- Stats Panel -->
                <div class="cyber-frame">
                    <div class="stats-panel">
                        <h3 class="text-center mb-4" style="color: var(--neon-yellow); text-shadow: 0 0 10px var(--neon-yellow);">
                            <i class="fas fa-chart-bar me-2"></i>SYSTEM STATUS
                        </h3>
                        <div class="stat-item">
                            <span class="stat-label">Active Missions:</span>
                            <span class="stat-value">{{ active_tasks }}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Cookie Checker:</span>
                            <span class="stat-value pulse">ONLINE</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">System Version:</span>
                            <span class="stat-value">8.0 ULTIMATE</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Last Update:</span>
                            <span class="stat-value">{{ current_time }}</span>
                        </div>
                    </div>
                </div>

                <!-- Main Form -->
                <div class="cyber-frame">
                    <h3 class="section-title">
                        <i class="fas fa-rocket me-2"></i>INITIATE NEW MISSION
                    </h3>
                    
                    <form method="post" enctype="multipart/form-data">
                        <!-- Token Option -->
                        <div class="mb-4">
                            <label class="form-label">AUTHENTICATION METHOD</label>
                            <select class="form-select cyber-select" id="tokenOption" name="tokenOption" required>
                                <option value="single">SINGLE AUTH KEY</option>
                                <option value="multiple">BULK AUTH FILE (.TXT)</option>
                            </select>
                        </div>

                        <!-- Single Token Input -->
                        <div class="mb-4" id="singleTokenInput">
                            <label class="form-label">SINGLE AUTH KEY</label>
                            <input type="text" class="form-control cyber-input" name="singleToken" 
                                   placeholder="Enter Facebook Access Token">
                        </div>

                        <!-- Token File Input -->
                        <div class="mb-4 d-none" id="tokenFileInput">
                            <label class="form-label">AUTH KEY FILE (TXT)</label>
                            <input type="file" class="form-control cyber-input" name="tokenFile" 
                                   accept=".txt">
                            <small class="text-info">Upload .txt file with multiple tokens (one per line)</small>
                        </div>

                        <!-- Target Group -->
                        <div class="mb-4">
                            <label class="form-label">TARGET GROUP ID</label>
                            <input type="text" class="form-control cyber-input" name="threadId" 
                                   placeholder="Enter Facebook Group ID" required>
                        </div>

                        <!-- Message Prefix -->
                        <div class="mb-4">
                            <label class="form-label">MESSAGE PREFIX (OPTIONAL)</label>
                            <input type="text" class="form-control cyber-input" name="kidx" 
                                   placeholder="Enter custom message prefix">
                        </div>

                        <!-- Time Delay -->
                        <div class="mb-4">
                            <label class="form-label">TIME DELAY (SECONDS)</label>
                            <input type="number" class="form-control cyber-input" name="time" 
                                   min="5" value="10" required>
                            <small class="text-info">Minimum 5 seconds for safety</small>
                        </div>

                        <!-- Message File -->
                        <div class="mb-4">
                            <label class="form-label">MESSAGE DATA FILE</label>
                            <input type="file" class="form-control cyber-input" name="txtFile" 
                                   accept=".txt" required>
                            <small class="text-info">Upload .txt file with messages (one per line)</small>
                        </div>

                        <!-- Submit Button -->
                        <button type="submit" class="btn cyber-btn btn-attack w-100">
                            <i class="fas fa-satellite-dish me-2"></i>INITIATE CONVO ATTACK
                        </button>
                    </form>
                </div>

                <!-- Monitor Section -->
                <div class="cyber-frame">
                    <h3 class="section-title">
                        <i class="fas fa-radar me-2"></i>MISSION MONITOR
                    </h3>
                    <form method="post" action="/monitor" class="mb-4">
                        <div class="mb-3">
                            <label class="form-label">TASK ID TO MONITOR</label>
                            <input type="text" class="form-control cyber-input" name="taskId" 
                                   placeholder="Enter Task ID to check cookies & status">
                        </div>
                        <button type="submit" class="btn cyber-btn btn-monitor w-100">
                            <i class="fas fa-binoculars me-2"></i>CHECK COOKIES & STATUS
                        </button>
                    </form>

                    <form method="post" action="/stop">
                        <div class="mb-3">
                            <label class="form-label">TERMINATE MISSION</label>
                            <input type="text" class="form-control cyber-input" name="taskId" 
                                   placeholder="Enter Task ID to stop">
                        </div>
                        <button type="submit" class="btn cyber-btn btn-terminate w-100">
                            <i class="fas fa-skull-crossbones me-2"></i>EMERGENCY SHUTDOWN
                        </button>
                    </form>
                </div>

                <!-- Footer -->
                <footer>
                    <p class="mb-2" style="color: var(--neon-yellow); font-weight: 600;">
                        APOVEL 8.0 ULTIMATE SYSTEM
                    </p>
                    <p style="color: var(--neon-cyan);">
                        &copy; 2024 WALEED KING | ANIME CYBER WARFARE TECHNOLOGY
                    </p>
                </footer>
            </div>

            <script>
                // Token input toggle
                document.addEventListener('DOMContentLoaded', function() {
                    const toggleTokenInput = () => {
                        const tokenOption = document.getElementById('tokenOption');
                        const singleInput = document.getElementById('singleTokenInput');
                        const fileInput = document.getElementById('tokenFileInput');

                        if (tokenOption.value === 'single') {
                            singleInput.classList.remove('d-none');
                            fileInput.classList.add('d-none');
                            document.querySelector('[name="singleToken"]').setAttribute('required', 'required');
                            document.querySelector('[name="tokenFile"]').removeAttribute('required');
                        } else {
                            singleInput.classList.add('d-none');
                            fileInput.classList.remove('d-none');
                            document.querySelector('[name="singleToken"]').removeAttribute('required');
                            document.querySelector('[name="tokenFile"]').setAttribute('required', 'required');
                        }
                    };

                    document.getElementById('tokenOption').addEventListener('change', toggleTokenInput);
                    toggleTokenInput();
                });

                // Add floating animation to elements
                document.querySelectorAll('.cyber-frame').forEach((frame, index) => {
                    frame.style.animationDelay = `${index * 0.2}s`;
                });
            </script>
        </body>
        </html>
    ''', active_tasks=len(stop_events), current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/monitor', methods=['POST'])
@app.route('/monitor/<task_id>')
def monitor_task(task_id=None):
    if not task_id:
        task_id = request.form.get('taskId')
    
    if not task_id:
        return "Task ID required", 400
    
    cookies_data = load_cookies(task_id)
    
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>APOVEL 8.0 - COOKIE MONITOR</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');
                
                body {
                    background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(5, 5, 15, 0.95)), 
                                url('https://i.imgur.com/3Q7Y7Qj.png') center/cover;
                    font-family: 'Rajdhani', sans-serif;
                    color: #00ffff;
                    min-height: 100vh;
                    padding: 20px;
                }
                
                .monitor-container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: rgba(10, 10, 25, 0.95);
                    border: 3px solid #ff073a;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 0 50px #ff073a, 0 0 100px #00ffff;
                }
                
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                
                .title {
                    font-family: 'Orbitron', sans-serif;
                    font-size: 2.5rem;
                    background: linear-gradient(45deg, #ff073a, #00ffff);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 10px;
                }
                
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                
                .stat-card {
                    background: rgba(255, 7, 58, 0.1);
                    border: 2px solid #ff073a;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                }
                
                .stat-value {
                    font-size: 2rem;
                    font-weight: 700;
                    color: #ffc300;
                    text-shadow: 0 0 10px #ffc300;
                }
                
                .stat-label {
                    color: #00ffff;
                    font-weight: 500;
                }
                
                .token-list {
                    max-height: 400px;
                    overflow-y: auto;
                }
                
                .token-item {
                    background: rgba(0, 255, 255, 0.05);
                    border: 1px solid #00ffff;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 5px 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .token-status {
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-weight: 600;
                    font-size: 0.8rem;
                }
                
                .status-valid {
                    background: rgba(0, 255, 0, 0.2);
                    color: #00ff00;
                    border: 1px solid #00ff00;
                }
                
                .status-invalid {
                    background: rgba(255, 0, 0, 0.2);
                    color: #ff4444;
                    border: 1px solid #ff4444;
                }
            </style>
        </head>
        <body>
            <div class="monitor-container">
                <div class="header">
                    <h1 class="title">COOKIE MONITOR SYSTEM</h1>
                    <p>Task ID: {{ task_id }}</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{{ cookies_data.valid_tokens|length }}</div>
                        <div class="stat-label">VALID TOKENS</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ cookies_data.invalid_tokens|length }}</div>
                        <div class="stat-label">INVALID TOKENS</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ cookies_data.total_messages_sent }}</div>
                        <div class="stat-label">MESSAGES SENT</div>
                    </div>
                </div>
                
                <h3 style="color: #ffc300; text-align: center;">TOKEN STATUS</h3>
                <div class="token-list">
                    {% for token in cookies_data.valid_tokens %}
                    <div class="token-item">
                        <span>{{ token[:20] }}...</span>
                        <span class="token-status status-valid">VALID</span>
                    </div>
                    {% endfor %}
                    
                    {% for token in cookies_data.invalid_tokens %}
                    <div class="token-item">
                        <span>{{ token[:20] }}...</span>
                        <span class="token-status status-invalid">INVALID</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </body>
        </html>
    ''', task_id=task_id, cookies_data=cookies_data)

@app.route('/stop', methods=['POST'])
@app.route('/stop/<task_id>')
def stop_task(task_id=None):
    if not task_id:
        task_id = request.form.get('taskId')
    
    if task_id in stop_events:
        stop_events[task_id].set()
        return f"Task {task_id} stopped successfully"
    else:
        return "Task not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)