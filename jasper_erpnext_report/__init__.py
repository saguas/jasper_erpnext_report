from __future__ import unicode_literals
import frappe
from wsserver import wsserver
from threading import Thread
import sys, socket
#print('Press Ctrl+C')
#signal.pause()
#import signal

def MyThread (args):
	wsserver.wsstart()

def start_server():
	try:
		thread = Thread(target = MyThread, args = (10, ))
		thread.daemon = True
		thread.start()
	except KeyboardInterrupt:
		print "Ctrl-c pressed ..."
		sys.exit(1)


def start_tornado():
	start_server()

def start_socketio():
	start_server()

#def start_socketio():
#	wsserver.wsstart()

#print "continue...."

jasper_session_obj = frappe.local("jasper_session_obj")
jasper_session = frappe.local("jasper_session")
pyjnius = False

"""s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = s.connect_ex(('', 8888))


if result == 0:
	print('socket is open')
	s.close()
else:
	#wsserver.wsstart()
	#start_tornado()
	start_socketio()
"""




#def Exit_gracefully(signal, frame):
#    sys.exit(0)

#signal.signal(signal.SIGINT, Exit_gracefully)