///<reference path='./typescript/src/compiler/typescript.ts'/>
///<reference path='./typescript/src/services/typescriptServices.ts'/>
///<reference path='node.d.ts'/>
///<reference path='scriptInfo.ts'/>

module SublimeTS {

	import fs = module('fs');
	import net = module('net');

	class MyLanguageServiceHost implements Services.ILanguageServiceHost {
		private scripts : TypeScript.ScriptInfo[];

		constructor () {
			this.scripts = new Array();
			this.addScript('lib.d.ts', fs.readFileSync('lib.d.ts').toString('utf8'));
		}

		getCompilationSettings(): TypeScript.CompilationSettings {
			return new TypeScript.CompilationSettings();
		}

		getScriptCount(): number {
			return this.scripts.length;
		}

		getScriptId(scriptIndex: number): string {
			return this.scripts[scriptIndex].name;
		}

		getScriptSourceText(scriptIndex: number, start: number, end: number): string {
			return this.scripts[scriptIndex].content.substr(start, end);
		}

		getScriptSourceLength(scriptIndex: number): number {
			return this.scripts[scriptIndex].content.length;
		}

		getScriptIsResident(scriptIndex: number): bool {
			return true;
		}

		getScriptVersion(scriptIndex: number): number {
			return this.scripts[scriptIndex].version;
		}

		getScriptEditRangeSinceVersion(scriptIndex: number, scriptVersion: number): TypeScript.ScriptEditRange {
			return this.scripts[scriptIndex].getEditRangeSinceVersion(scriptVersion);
		}

		information(): bool {
			return false;
		}

		debug(): bool {
			return false;
		}

		warning(): bool {
			return false;
		}

		error(): bool {
			return false;
		}

		fatal(): bool {
			return false;
		}

		log(s: string): void {

		}

		public addScript(name: string, content: string) {
			this.scripts.push(new TypeScript.ScriptInfo(name, content, true, 20));
		}

		public updateRange(range: UpdateRangeCommandObject) {
			for (var i in this.scripts) {
				if(this.scripts[i].name == range.name) {
					this.scripts[i].editContent(range.start, range.end, range.content);
					console.log(this.scripts[i].content)
					return true;
				}
			}
			return false;
		}
	}

	class CommandObject {
		public command: string;
		
		public initWithData(obj: any) {
			if (obj.command != undefined && typeof(obj.command) == 'string') {
				this.command = obj.command;
				return this;
			}
			else return null;
		}
	}

	class AddScriptCommandObject extends CommandObject {
		public name: string;
		public content: string;

		public initWithData(obj: any) {
			if (super.initWithData(obj) 
				&& obj.name != undefined && typeof(obj.name) == 'string'
				&& obj.content != undefined && typeof(obj.content) == 'string') {
				this.name = obj.name;
				this.content = obj.content;
				return this;
			}
			else return null;
			
		}
	}

	class GetCompletionsCommandObject extends CommandObject {
		public fileName : string;
		public position : number;
		public isMember : bool;

		public initWithData(obj: any) {
			if(super.initWithData(obj)
				&& obj.name != undefined && typeof(obj.name) == 'string'
				&& obj.position != undefined && typeof(obj.position) == 'number'
				&& obj.isMember != undefined && typeof(obj.isMember) == 'boolean') {
				this.fileName = obj.name;
				this.position = obj.position;
				this.isMember = obj.isMember;
				return this;
			}
			else return null;
		}
	}

	class UpdateRangeCommandObject extends CommandObject {
		public start : number;
		public end : number;
		public content : string;
		public name: string;

		public initWithData(obj: any) {
			if(super.initWithData(obj)
				&& obj.start != undefined && typeof(obj.start) == 'number'
				&& obj.end != undefined && typeof(obj.end) == 'number'
				&& obj.content != undefined && typeof(obj.content) == 'string'
				&& obj.name != undefined && typeof(obj.name) == 'string') {
				this.start = obj.start;
				this.end = obj.end;
				this.content = obj.content;
				this.name = obj.name;
				return this;
			}
			else return null;
		}
	}

	export class Server {
		private server : net.Server;
		private recvState = 'idle';
		private recvBuffer : NodeBuffer;
		private recvLength = 0;
		private lsh : MyLanguageServiceHost;
		private ls : Services.ILanguageService;

		constructor(socketPath : string) {
			this.recvBuffer = null;
			var langServiceFactory = new Services.TypeScriptServicesFactory();
			this.lsh = new MyLanguageServiceHost();
			this.ls = langServiceFactory.createLanguageService(this.lsh);


			this.server = net.createServer(sock => {
				console.log("Connection accepted");
				sock.on('end', function() {
					console.log("Connection closed");
					});
				sock.on('timeout', sock => {
					console.log("Connection timed out");
					});
				sock.on('data', data => {
					console.log("Data received");
					// Add the data
					if (this.recvBuffer != null) {
						Buffer.concat([this.recvBuffer, data]);
					}
					else {
						this.recvBuffer = data;
					}

					// Process
					this.processData(sock);

					});
				});

			this.server.listen(socketPath, function() {
				console.log("Server started");
				});
		}

		private processData(sock: net.NodeSocket) {
			var stop = false;

			while (!stop) {
				if (this.recvState == 'idle') {
					this.recvLength = this.recvBuffer.readUInt32LE(0, true);
					this.recvBuffer = this.recvBuffer.slice(4);
					console.log("Length: " + this.recvLength);
					console.log("Remaining: " + this.recvBuffer.length);
				}

				if (this.recvBuffer.length >= this.recvLength) {
					// Parse
					var data = this.recvBuffer.toString('utf8', 0, this.recvLength);
					this.processCommandObject(sock, JSON.parse(data));

					// Advance
					if (this.recvBuffer.length > this.recvLength) {
						this.recvBuffer = this.recvBuffer.slice(this.recvLength);	
					}
					else {
						this.recvBuffer = null;
					}

					// Reset
					this.recvState = 'idle';
					this.recvLength = 0;
				}

				if (this.recvBuffer == null || this.recvLength > this.recvBuffer.length) {
					stop = true;
				}
			}
		}

		private processCommandObject(sock: net.NodeSocket, obj: any) {
			var commandObj = new CommandObject().initWithData(obj);
			if (commandObj) {
				switch (obj.command) {
					case 'addScript':
					var addObj = new AddScriptCommandObject().initWithData(obj);
					//console.log(addObj)
					if (addObj) {
						this.lsh.addScript(addObj.name, addObj.content)
						this.writeOkResponse(sock);
					}
					else {
						this.writeResponse(sock, 'Error: Malformed command object (addScript)');
					}
					break;

					case 'updateRange':
					var rangeObj = new UpdateRangeCommandObject().initWithData(obj);
					//console.log(rangeObj);
					if (rangeObj) {
						if (this.lsh.updateRange(rangeObj)) {
							this.writeOkResponse(sock);
						}
						else {
							this.writeErrorResponse(sock, 'Unknown script name');
						}
					}
					else {
						this.writeErrorResponse(sock, 'Error: Malformed command (updateRange)');
					}
					break; 

					case 'getCompletionsAtPosition':
					var compObj = new GetCompletionsCommandObject().initWithData(obj)
					//console.log(compObj)
					if (compObj) {
						var completions = this.ls.getCompletionsAtPosition(compObj.fileName, compObj.position, compObj.isMember);
						this.writeResponse(sock, completions);
					}
					else {
						this.writeErrorResponse(sock, 'Malformed command object (getCompletionsAtPosition)');
					}
					break;

					default:
					this.writeResponse(sock, 'Error: Unknown command')
					break;
				}
			}
			else {
				this.writeErrorResponse(sock, 'Error: Malformed command object');
			}
		}

		private writeErrorResponse(sock: net.NodeSocket, msg: string) {
			this.writeResponse(sock, {status: 'error', message: msg});
		}

		private writeOkResponse(sock: net.NodeSocket) {
			this.writeResponse(sock, {status: 'ok'});
		}

		private writeResponse(sock: net.NodeSocket, obj: Object) {
			var strData = JSON.stringify(obj);
			var buffer : NodeBuffer = new Buffer(4);
			buffer.writeUInt32LE(strData.length, 0);
			sock.write(buffer);
			sock.write(strData);
		}
	}

}
	

var myServer = new SublimeTS.Server('/tmp/ahkatsls');
