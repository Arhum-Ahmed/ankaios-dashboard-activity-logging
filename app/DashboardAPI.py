from Logger import Logger
from flask import Flask, render_template, Response, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from AnkCommunicationService import AnkCommunicationService
from ActivityLogger import ActivityLogger
import uuid
import os
import csv
import io

class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        variable_start_string='%%',
        variable_end_string='%%',
    ))

dashboard = CustomFlask(__name__, static_folder='static/assets/', template_folder='static/')
dashboard.config['SECRET_KEY'] = str(uuid.uuid4())

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(dashboard)

logger = Logger.get_custom_logger()

# Initialize Activity Logger
activity_logger = ActivityLogger()

# Pass activity_logger to AnkCommunicationService
ank_comm_service = AnkCommunicationService(activity_logger=activity_logger)

DEFAULT_PASSWORD = ""

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@dashboard.route('/', methods=['GET'])
@dashboard.route('/index.html', methods=['GET'])
def home():
    return render_template('index.html')

@dashboard.route('/login', methods=['POST'])
def login():
    pwd = request.json['pwd']['_value']
    if pwd == os.environ.get('PASSWORD', DEFAULT_PASSWORD) or not os.environ.get('PASSWORD', DEFAULT_PASSWORD):
        user = User(str(uuid.uuid4()))
        login_user(user)
        return Response("Logged in.", status=200)
    else:
        return Response("Wrong password.", status=401)

@dashboard.route('/logout')
@login_required
def logout():
    logout_user()
    return Response("Logged out.", status=200)

@dashboard.route('/checkAuthentication', methods=['GET'])
def checkAuthentication():
    if current_user.is_authenticated:
        return Response("Authenticated.", status=200)
    elif not os.environ.get('PASSWORD', DEFAULT_PASSWORD):
        user = User(str(uuid.uuid4()))
        login_user(user)
        return Response("Authenticated.", status=200)
    else:
        print("user not authenticated.", current_user)
        return Response("Not authenticated.", status=401)

@dashboard.route('/setNewPwd', methods=['POST'])
def setNewPwd():
    pwd_old = request.json['pwd']['_value']
    pwd_new = request.json['newPwd']['_value']
    if pwd_old == os.environ.get('PASSWORD', DEFAULT_PASSWORD):
        os.environ['PASSWORD'] = pwd_new
        return Response("Changed password.", status=200)
    else:
        return Response("Did not change password.", status=401)

@dashboard.route('/debug')
def debug():
    return render_template('debug.html')

@dashboard.route('/completeState', methods=['GET'])
@login_required
def get_complete_state():
    return ank_comm_service.get_complete_state()

@dashboard.route('/addNewWorkload', methods=['POST'])
@login_required
def add_new_workload():
    user_id = current_user.id if current_user.is_authenticated else "anonymous"
    print(ank_comm_service.add_new_workload(request.json, user_id=user_id))
    return Response("Workload added.", status=200, mimetype='application/json')

@dashboard.route('/deleteWorkloads', methods=['POST'])
@login_required
def delete_workloads():
    user_id = current_user.id if current_user.is_authenticated else "anonymous"
    print(ank_comm_service.deleteWorkloads(request.json, user_id=user_id))
    return Response("Workloads deleted.", status=200, mimetype='application/json')

@dashboard.route('/updateConfig', methods=['PUT'])
@login_required
def update_config():
    user_id = current_user.id if current_user.is_authenticated else "anonymous"
    print(ank_comm_service.update_config(request.json, user_id=user_id))
    return Response("Config updated.", status=200, mimetype='application/json')

@dashboard.route('/writeAccess', methods=['GET'])
def get_write_access():
    return ank_comm_service.get_write_access()

# ========== ACTIVITY LOGGER ENDPOINTS ==========

@dashboard.route('/activityLogs', methods=['GET'])
@login_required
def get_activity_logs():
    """Get activity logs with optional filters"""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        action_filter = request.args.get('action')
        workload_filter = request.args.get('workload')
        user_filter = request.args.get('user')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logs = activity_logger.get_logs(
            limit=limit,
            offset=offset,
            action_filter=action_filter,
            workload_filter=workload_filter,
            user_filter=user_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        total = activity_logger.get_total_count(
            action_filter=action_filter,
            workload_filter=workload_filter,
            user_filter=user_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'logs': logs,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error fetching activity logs: {e}")
        return Response("Failed to fetch logs.", status=500)

@dashboard.route('/exportLogs', methods=['GET'])
@login_required
def export_logs():
    """Export activity logs as CSV"""
    try:
        # Get all logs without pagination
        action_filter = request.args.get('action')
        workload_filter = request.args.get('workload')
        user_filter = request.args.get('user')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logs = activity_logger.get_logs(
            limit=10000,  # Large limit for export
            offset=0,
            action_filter=action_filter,
            workload_filter=workload_filter,
            user_filter=user_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Timestamp', 'User ID', 'Action', 'Workload Name', 'Agent', 'Status', 'Metadata'])
        
        # Write data
        for log in logs:
            writer.writerow([
                log['id'],
                log['timestamp'],
                log['user_id'],
                log['action'],
                log['workload_name'] or '',
                log['agent'] or '',
                log['status'],
                str(log['metadata']) if log['metadata'] else ''
            ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=activity_logs.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        return Response("Failed to export logs.", status=500)

def run(ip="0.0.0.0", p="5001"):
    logger.info(f"Starting the dashboard api ...")
    dashboard.run(host=ip, port=p)