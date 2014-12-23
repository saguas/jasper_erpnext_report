__author__ = 'luissaguas'
#from tornado import websocket, web, ioloop, wsgi
#import wsgiref.simple_server
import sys

#import werkzeug.serving


#from gevent import monkey
#from bottle import Bottle, request
from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin


#cl = []


class ChatNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):
	def on_nickname(self, nickname):
		self.request['nicknames'].append(nickname)
		self.socket.session['nickname'] = nickname
		self.broadcast_event('announcement', '%s has connected' % nickname)
		self.broadcast_event('nicknames', self.request['nicknames'])
		# Just have them join a default-named room
		self.join('main_room')

	def recv_disconnect(self):
		# Remove nickname from the list.
		nickname = self.socket.session['nickname']
		self.request['nicknames'].remove(nickname)
		self.broadcast_event('announcement', '%s has disconnected' % nickname)
		self.broadcast_event('nicknames', self.request['nicknames'])

		self.disconnect(silent=True)

	def on_message(self, msg):
		self.emit_to_room('main_room', 'msg_to_room',
			self.socket.session['nickname'], msg)

	def recv_message(self, message):
		print "PING!!!", message

class Application(object):
	def __init__(self):
		self.buffer = []
		# Dummy request object to maintain state between Namespace
		# initialization.
		self.request = {
			'nicknames': [],
		}

	def __call__(self, environ, start_response):
		path = environ['PATH_INFO'].strip('/')
		"""if not path:
			start_response('200 OK', [('Content-Type', 'text/html')])
			return ['<h1>Welcome. '
				'Try the <a href="/chat.html">chat</a> example.</h1>']

		if path.startswith('static/') or path == 'chat.html':
			try:
				data = open(path).read()
			except Exception:
				return not_found(start_response)

			if path.endswith(".js"):
				content_type = "text/javascript"
			elif path.endswith(".css"):
				content_type = "text/css"
			elif path.endswith(".swf"):
				content_type = "application/x-shockwave-flash"
			else:
				content_type = "text/html"

			start_response('200 OK', [('Content-Type', content_type)])
			return [data]
		"""
		if path.startswith("socket.io"):
			#self.request['HTTP_ORIGIN'] = "http://localhost:8888"
			socketio_manage(environ, {'/chat': ChatNamespace}, self.request)
		else:
			return not_found(start_response)


def not_found(start_response):
	start_response('404 Not Found', [])
	return ['<h1>Not Found</h1>']

def wsstart():
	try:
		print "listen.... 8888"
		#monkey.patch_all()
		SocketIOServer(('0.0.0.0', 8888), Application(),
			resource="socket.io", policy_server=False).serve_forever()
			#policy_listener=('0.0.0.0', 10843)).serve_forever()
	except KeyboardInterrupt:
		print "Ctrl-c pressed ..."
		sys.exit(1)


"""
#tornado works as well as socketio
class SocketHandler(websocket.WebSocketHandler):

	def open(self):
		print "open"
		if self not in cl:
			cl.append(self)

	def on_close(self):
		print "closed"
		if self in cl:
			cl.remove(self)

	def on_message(self, message):
		print "recived {}".format(message)
		self.write_message(u"You said: " + message)

	def check_origin(self, origin):
		return True
"""
"""def wsstart2():
	app = web.Application([
		(r'/ws', SocketHandler)
	])
	print "listen.... 8888"
	try:
		wsgi_app = wsgi.WSGIAdapter(app)
		server = wsgiref.simple_server.make_server('', 8888, wsgi_app)
		server.serve_forever()
	except KeyboardInterrupt:
		print "Ctrl-c pressed ..."
		sys.exit(1)"""
"""
def wsstart():

	app = web.Application([
		(r'/ws', SocketHandler)
	])
	app.listen(8889)
	print "listen.... 8888"
	try:
		ioloop.IOLoop.instance().start()
	except KeyboardInterrupt:
		print "Ctrl-c pressed ..."
		ioloop.IOLoop.instance().stop()
		sys.exit(1)

def stopTornado():
	ioloop.IOLoop.instance().stop()
"""