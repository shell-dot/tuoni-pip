import base64

class TuoniDefaultCommand:
    def __init__(self, command_type, command_conf):
        self.command_type = command_type
        self.command_conf = command_conf
        self.execution_conf = None
        self.files = None

class TuoniDefaultPluginCommand(TuoniDefaultCommand):
    def __init__(self, command_type, command_conf, execution_conf = None):
        super().__init__(command_type, command_conf)
        if isinstance(execution_conf, ExecutionNew):
            self.execution_conf = {
                "execType": "NEW",
                "executable": execution_conf.proc_name,
                "suspended": execution_conf.suspended
            }
        elif isinstance(execution_conf, ExecutionExisting):
            self.execution_conf = {
                "execType": "EXISTING",
                "pid": execution_conf.pid
            }
        else:
            self.execution_conf = execution_conf


class ExecutionNew:
    def __init__(self, proc_name="notepad.exe", suspended=True):
        self.proc_name = proc_name
        self.suspended = suspended

class ExecutionExisting:
    def __init__(self, pid):
        self.pid = pid


#########################
## Native commands
#########################
class TuoniCommandBof(TuoniDefaultCommand):
    _class_base_type = "bof"
    def __init__(self, bof_file, method =  "go", inputArgs = None, inputArgsEncoding = None, inputAsBytes = None):
        super().__init__("bof", {"method": method, "inputArgs": inputArgs, "inputArgsEncoding": inputArgsEncoding, "inputAsBytes": inputAsBytes})
        self.files = {"bofFile": ["filename.bin", bof_file]}


class TuoniCommandCd(TuoniDefaultCommand):
    _class_base_type = "cd"
    def __init__(self, dir):
        super().__init__("cd", {"dir": dir})


class TuoniCommandDie(TuoniDefaultCommand):
    _class_base_type = "die"
    def __init__(self):
        super().__init__("die", {})


class TuoniCommandLs(TuoniDefaultCommand):
    _class_base_type = "ls"
    def __init__(self, dir, depth = 1):
        super().__init__("ls", {"dir": dir, "depth": depth})


class TuoniCommandCmd(TuoniDefaultPluginCommand):
    _class_base_type = "cmd"
    def __init__(self, command, stdin = None, outputEncoding = None):
        super().__init__("cmd", {"command": command, "stdin": stdin, "outputEncoding": outputEncoding})


class TuoniCommandJobs(TuoniDefaultPluginCommand):
    _class_base_type = "jobs"
    def __init__(self):
        super().__init__("jobs", {})


class TuoniCommandProclist(TuoniDefaultPluginCommand):
    _class_base_type = "ps"
    def __init__(self):
        super().__init__("ps", {})


class TuoniCommandRun(TuoniDefaultPluginCommand):
    _class_base_type = "run"
    def __init__(self, cmdline, output = True, stdin = None, unicode = None, outputEncoding = None):
        super().__init__("run", {"cmdline": cmdline, "output": output, "stdin": stdin, "unicode": unicode, "outputEncoding": outputEncoding})


class TuoniCommandPowershell(TuoniDefaultPluginCommand):
    _class_base_type = "powershell"
    def __init__(self, command = None, stdin = None, outputEncoding = None):
        super().__init__("powershell", {"command": command, "stdin": stdin, "outputEncoding": outputEncoding})


class TuoniCommandSleep(TuoniDefaultPluginCommand):
    _class_base_type = "sleep"
    def __init__(self, sleep_time, sleep_random):
        super().__init__("sleep", {"sleep": sleep_time, "sleepRandom": sleep_random})

#########################
## Native token commands
#########################
class TuoniCommandTokenSteal(TuoniDefaultPluginCommand):
    _class_base_type = "token-steal"
    def __init__(self, pid):
        super().__init__("token-steal", {"pid": pid})


class TuoniCommandTokenDeleteAll(TuoniDefaultPluginCommand):
    _class_base_type = "token-del-all"
    def __init__(self):
        super().__init__("token-del-all", {})


class TuoniCommandTokenDelete(TuoniDefaultPluginCommand):
    _class_base_type = "token-add"
    def __init__(self, nr):
        super().__init__("token-add", {"nr": nr})


class TuoniCommandTokenList(TuoniDefaultPluginCommand):
    _class_base_type = "token-list"
    def __init__(self):
        super().__init__("token-list", {})


class TuoniCommandTokenMake(TuoniDefaultPluginCommand):
    _class_base_type = "token-make"
    def __init__(self, username, password):
        super().__init__("token-make", {"username": username, "password": password})


class TuoniCommandTokenUse(TuoniDefaultPluginCommand):
    _class_base_type = "token-use"
    def __init__(self, nr):
        super().__init__("token-use", {"nr": nr})


#########################
## Plugin FS commands
#########################

class TuoniCommandRm(TuoniDefaultPluginCommand):
    _class_base_type = "rm"
    def __init__(self, filepath, execution_conf = None):
        super().__init__("rm", {"filepath": filepath}, execution_conf)


class TuoniCommandDownload(TuoniDefaultPluginCommand):
    _class_base_type = "download"
    def __init__(self, filepath, execution_conf = None):
        super().__init__("download", {"filepath": filepath}, execution_conf)


class TuoniCommandUpload(TuoniDefaultPluginCommand):
    _class_base_type = "upload"
    def __init__(self, filepath, data, execution_conf = None):
        super().__init__("upload", {"filepath": filepath}, execution_conf)
        self.files = {"file": ["filename.bin", data]}


class TuoniCommandCp(TuoniDefaultPluginCommand):
    _class_base_type = "cp"
    def __init__(self, source, destination, execution_conf = None):
        super().__init__("cp", {"source": source, "destination": destination}, execution_conf)


class TuoniCommandMv(TuoniDefaultPluginCommand):
    _class_base_type = "mv"
    def __init__(self, source, destination, execution_conf = None):
        super().__init__("mv", {"source": source, "destination": destination}, execution_conf)


class TuoniCommandMkdir(TuoniDefaultPluginCommand):
    _class_base_type = "mkdir"
    def __init__(self, dirpath, execution_conf = None):
        super().__init__("mkdir", {"dirpath": dirpath}, execution_conf)


#########################
## Plugin NET commands
#########################

class TuoniCommandSocks5(TuoniDefaultPluginCommand):
    _class_base_type = "socks5"
    def __init__(self, port, execution_conf = None):
        super().__init__("socks5", {"port": port}, execution_conf)


class TuoniCommandConnectTcp(TuoniDefaultPluginCommand):
    _class_base_type = "connect-tcp"
    def __init__(self, host, port, execution_conf = None):
        super().__init__("connect-tcp", {"host": host, "port": port}, execution_conf)

#########################
## Plugin OS commands
#########################


class TuoniCommandexecuteAssembly(TuoniDefaultPluginCommand):
    _class_base_type = "execute-assembly"
    def __init__(self, executable, parameters, execution_conf = None):
        super().__init__("execute-assembly", {"parameters": parameters}, execution_conf)
        self.files = {"executable": ["filename.bin", executable]}


class TuoniCommandInject(TuoniDefaultPluginCommand):
    _class_base_type = "inject"
    def __init__(self, shellcode, execution_conf = None):
        super().__init__("inject", {}, execution_conf)
        self.files = {"shellcode": ["filename.bin", shellcode]}


class TuoniCommandProcinfo(TuoniDefaultPluginCommand):
    _class_base_type = "procinfo"
    def __init__(self, execution_conf = None):
        super().__init__("procinfo", {}, execution_conf)


class TuoniCommandScreenshot(TuoniDefaultPluginCommand):
    _class_base_type = "screenshot"
    def __init__(self, execution_conf = None):
        super().__init__("screenshot", {}, execution_conf)


class TuoniCommandSpawn(TuoniDefaultPluginCommand):
    _class_base_type = "spawn"
    def __init__(self, payloadId, encrypted_communication = True, execution_conf = None):
        super().__init__("spawn", {"payloadId": payloadId, "encryptedCommunication": encrypted_communication}, execution_conf)


class TuoniCommandJumpService(TuoniDefaultPluginCommand):
    _class_base_type = "jump-service"
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, servicePath = None, serviceName = None, serviceDisplayName = None, cleanup = None, username = None, password = None, execution_conf = None):
        super().__init__("jump-service", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "servicePath":  servicePath, "serviceName":  serviceName, "serviceDisplayName":  serviceDisplayName, "cleanup":  cleanup, "username":  username, "password": password}, execution_conf)


class TuoniCommandJumpWinrm(TuoniDefaultPluginCommand):
    _class_base_type = "jump-winrm"
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, executablePath = None, customPowershell = None, username = None, password = None, execution_conf = None):
        super().__init__("jump-winrm", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "executablePath":  executablePath, "customPowershell":  customPowershell, "username":  username, "password": password}, execution_conf)


class TuoniCommandJumpWmi(TuoniDefaultPluginCommand):
    _class_base_type = "jump-wmi"
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, cmdline = None, username = None, password = None, execution_conf = None):
        super().__init__("jump-wmi", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "cmdline":  cmdline, "username":  username, "password": password}, execution_conf)


class TuoniCommandJumpSsh(TuoniDefaultPluginCommand):
    _class_base_type = "jump-ssh"
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, cmdline = None, username = None, password = None, privateKeyPEM = None, privateKeyPassword = None, execution_conf = None):
        super().__init__("jump-ssh", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "cmdline":  cmdline, "username":  username, "password": password, "privateKeyPassword": privateKeyPassword}, execution_conf)
        self.files = {"privateKeyPEM": ["private.pem", privateKeyPEM]}

#########################
## Other commands
#########################
class TuoniCommandReverseShellCommunication(TuoniDefaultCommand):
    def __init__(self, input):
        super().__init__("cd", {"input": input})
        
