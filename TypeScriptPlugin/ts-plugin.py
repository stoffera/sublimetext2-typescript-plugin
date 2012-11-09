import sublime, sublime_plugin, socket, threading, Queue, struct, json

class TsEventsCommand(sublime_plugin.EventListener):
	lastPosition = 0
	signal = threading.Condition()
	completions = []
	
	def on_query_completions(self, view, prefix, locations):
		self.signal.acquire()
		name = view.file_name()
		if name == None:
			return []

		pos = locations[0]
		completions = []

		isMember = view.substr(sublime.Region(pos-1, pos)) == "."

		def cb(comps):
			self.signal.acquire()
			cmpl = json.loads(comps)
			self.completions = [(x['name'],x['name']) for x in cmpl['entries']]
			print("Got completins")
			self.signal.notifyAll()
			self.signal.release()
	

		tsServices.getCompletions(name, pos, isMember, cb)
		
		self.signal.wait(1.0)

		self.signal.release()
		c = self.completions
		self.completions = []
		return c

	def on_new(self, view):
		name = view.file_name()

		if name != None:
			tsServices.addScript(name,"",None)


	def on_load(self, view):
		name = view.file_name()
		rg = sublime.Region(0, view.size()-1)

		if name != None: 
			tsServices.addScript(name,view.substr(rg),None)

	def on_modified(self, view):
		name = view.file_name()
		if name == None:
			return
                
		selection = view.sel()
		if len(selection) > 1:
			raise Exception("Not supported")

		selection = selection[0]

		if selection.a != selection.b:
			raise Exception("Not supported")

		position = selection.a
                
	# TODO: Add support for delete, paste, etc
		command,options,redo = view.command_history(0, True)
		print(command)

		insertedText = None
		if command == 'insert':
			insertedText = view.substr(sublime.Region(self.lastPosition, position))
			tsServices.updateRange(name, self.lastPosition, self.lastPosition, insertedText, None)
		elif command == 'left_delete':
			insertedText = ''
			tsServices.updateRange(name, position, self.lastPosition, insertedText, None)
		elif command == 'commit_completions':
			# Inserted text is text between last known pos and current pos
			insertedText = view.substr(sublime.Region(self.lastPosition, position))
			tsServices.updateRange(name, self.lastPosition, self.lastPosition, insertedText, None)
		else:
			print(command)
			return
		
		

	# TODO: Detect member completion
		
		self.lastPosition = position



	def on_selection_modified(self, view):
		sel = view.sel()[0]
                # TODO: Handle nonempty and multiple selections
		if sel.a != sel.b:
			raise Exception("Not supported")
		self.lastPosition = sel.a
		print("Position: " + str(self.lastPosition))


class TypeScriptServices:
	comm = None
	def __init__(self):
		print("init ts services")
		self.comm = Communicator()
		self.comm.connect()

	def addScript(self, name, content, callback):
		obj = dict()
		command = 'addScript'
		obj['cmd'] = '{{"command":"{command}","name":"{name}","content":{content}}}'.format(
			name=name,
			content=json.dumps(content),
			command=command)
		obj['callback'] = callback
		self.comm.addSendCmd(obj)
	
	def getCompletions(self, name, pos, member, callback):
		obj = dict()
		command = "getCompletionsAtPosition"
		obj['cmd'] = '{{"command":"{command}","name":"{name}","position":{pos},"isMember":{member}}}'.format(
			name=name,
			command=command,
			pos=json.dumps(pos),
			member=json.dumps(member))
		obj['callback'] = callback
		self.comm.addSendCmd(obj)

	def getType(self, name, pos, callback):
		obj = dict()
		command = "getType"
		obj['cmd'] = '{{"command":"{command}","name":"{name}","position":{pos},"isMember":{member}}}'.format(
			name=name,
			command=command,
			pos=json.dumps(pos))
		obj['callback'] = callback
		self.comm.addSendCmd(obj)

	def updateRange(self, name, startPos, endPos, content, callback):
		obj = dict()
		command = "updateRange"
		obj['cmd'] = '{{"command":"{command}","name":"{name}","start":{start},"end":{end},"content":{content}}}'.format(
			name=name,
			command=command,
			start=json.dumps(startPos),
			end=json.dumps(endPos),
			content=json.dumps(content))
		obj['callback'] = callback
		self.comm.addSendCmd(obj)
	

class Communicator(threading.Thread):
	sockFile = "/tmp/ahkatsls"
	sockIP = ("127.0.0.1",1337)
	conn = None
	sendCmds = Queue.Queue()
	mutex = None

	def __init__(self):
		threading.Thread.__init__(self);
		self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM);
		self.mutex = threading.Semaphore()
		self.start()

	def connect(self):
		self.conn.connect((self.sockFile))

	def run(self):
		print("Server client thread started")
		while 1:
			cmd = self.nextSendCmd()
			strData = cmd["cmd"]

			size = len(strData)
			print("Sending ("+str(size)+") cmd: "+strData)
			
			pack = struct.pack("<i"+str(size)+"s",size,str(strData))
			
			self.conn.sendall(pack)
			respSize = self.conn.recv(4)
			# if len(respSize) != 4:
			# 	print("Receive header was not of length 4 bytes, exiting! Got: "+len(respSize))
			# 	return
			int_value = struct.unpack('<i',respSize)[0]
			print("Receive size: "+str(int_value))

			got = 0
			resp = ''
			while got < int_value:
				buf = self.conn.recv(int_value - got)
				got = got + len(buf)
				resp = resp + buf

			if 'callback' in cmd and cmd["callback"] != None:
				cmd["callback"](resp)


	def addSendCmd(self, jsonStr):
		self.sendCmds.put(jsonStr, False)

	def nextSendCmd(self):
		return self.sendCmds.get(True)
		
tsServices = TypeScriptServices()
