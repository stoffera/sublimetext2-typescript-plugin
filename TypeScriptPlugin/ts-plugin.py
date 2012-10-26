import sublime, sublime_plugin, socket, threading, Queue, struct, json

class TsEventsCommand(sublime_plugin.EventListener):
	lastSelection = ""
	mutex = threading.Semaphore(0)
	currentEditLineRegion = None;
	def on_query_completions(self, view, prefix, locations):
		name = view.file_name()
		if name == None:
			return []

		pos = locations[0]
		completions = []

		def cb(comps):
			print("Got completions: "+comps)
			cmpl = json.loads(comps)
			

		tsServices.getCompletions(name, pos, True, cb)
		#freeze
		#self.mutex.acquire()

		return completions

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

		r = view.sel()[0]
		r = view.line(r)
		if self.currentEditLineRegion != None and self.currentEditLineRegion.a == r.a and self.currentEditLineRegion.b == r.b:
			return

		text = view.substr(r)
		tsServices.updateRange(name, r.a, r.b, text, None)
		self.currentEditLineRegion = r



	def on_selection_modified(self, view): 
		txt = ""
		for region in view.sel(): 
			if not region.empty(): txt = txt + view.substr(region)
			if txt != self.lastSelection:
				self.lastSelection = txt;
				#print("sel. changed: "+txt) 



class TypeScriptServices:
	comm = None
	def __init__(self):
		print("init ts services")
		self.comm = Communicator()
		self.comm.connect()
		#self.addScript("/typescript/src/lanser.t","hej me dig", None)

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
	sockIP = "10.0.46.40"
	conn = None
	sendCmds = Queue.Queue()
	mutex = None

	def __init__(self):
		threading.Thread.__init__(self);
		#self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
		self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM);
		self.mutex = threading.Semaphore()
		self.start()

	def connect(self):
		#self.conn.connect((self.sockIP, 1337))
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
			resp = self.conn.recv(int_value);
			print("Got response: "+resp)

			if cmd["callback"] != None:
				cmd["callback"](resp)


	def addSendCmd(self, jsonStr):
		self.sendCmds.put(jsonStr, False)

	def nextSendCmd(self):
		return self.sendCmds.get(True)
		

tsServices = TypeScriptServices()