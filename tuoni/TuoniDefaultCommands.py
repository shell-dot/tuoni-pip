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
    def __init__(self, bof_file, method =  "go", inputArgs = None, inputArgsEncoding = None, inputAsBytes = None):
        super().__init__("bof", {"method": method, "inputArgs": inputArgs, "inputArgsEncoding": inputArgsEncoding, "inputAsBytes": inputAsBytes})
        self.files = {"bofFile": ["filename.bin", bof_file]}


class TuoniCommandCd(TuoniDefaultCommand):
    def __init__(self, dir):
        super().__init__("cd", {"dir": dir})


class TuoniCommandDie(TuoniDefaultCommand):
    def __init__(self):
        super().__init__("die", {})


class TuoniCommandLs(TuoniDefaultCommand):
    def __init__(self, dir, depth = 1):
        super().__init__("ls", {"dir": dir, "depth": depth})


class TuoniCommandCmd(TuoniDefaultPluginCommand):
    def __init__(self, command, stdin = None, outputEncoding = None):
        super().__init__("cmd", {"command": command, "stdin": stdin, "outputEncoding": outputEncoding})


class TuoniCommandJobs(TuoniDefaultPluginCommand):
    def __init__(self):
        super().__init__("jobs", {})


class TuoniCommandProclist(TuoniDefaultPluginCommand):
    def __init__(self):
        super().__init__("ps", {})


class TuoniCommandRun(TuoniDefaultPluginCommand):
    def __init__(self, cmdline, output = True, stdin = None, unicode = None, outputEncoding = None):
        super().__init__("run", {"cmdline": cmdline, "output": output, "stdin": stdin, "unicode": unicode, "outputEncoding": outputEncoding})


class TuoniCommandPowershell(TuoniDefaultPluginCommand):
    def __init__(self, command = None, stdin = None, outputEncoding = None):
        super().__init__("powershell", {"command": command, "stdin": stdin, "outputEncoding": outputEncoding})


class TuoniCommandSleep(TuoniDefaultPluginCommand):
    def __init__(self, sleep_time, sleep_random):
        super().__init__("sleep", {"sleep": sleep_time, "sleepRandom": sleep_random})

#########################
## Native token commands
#########################
class TuoniCommandTokenSteal(TuoniDefaultPluginCommand):
    def __init__(self, pid):
        super().__init__("token-steal", {"pid": pid})


class TuoniCommandTokenDeleteAll(TuoniDefaultPluginCommand):
    def __init__(self):
        super().__init__("token-del-all", {})


class TuoniCommandTokenDelete(TuoniDefaultPluginCommand):
    def __init__(self, nr):
        super().__init__("token-add", {"nr": nr})


class TuoniCommandTokenList(TuoniDefaultPluginCommand):
    def __init__(self):
        super().__init__("token-list", {})


class TuoniCommandTokenMake(TuoniDefaultPluginCommand):
    def __init__(self, username, password):
        super().__init__("token-make", {"username": username, "password": password})


class TuoniCommandTokenUse(TuoniDefaultPluginCommand):
    def __init__(self, nr):
        super().__init__("token-use", {"nr": nr})


#########################
## Plugin FS commands
#########################

class TuoniCommandRm(TuoniDefaultPluginCommand):
    def __init__(self, filepath, execution_conf = None):
        super().__init__("rm", {"filepath": filepath}, execution_conf)


class TuoniCommandDownload(TuoniDefaultPluginCommand):
    def __init__(self, filepath, execution_conf = None):
        super().__init__("download", {"filepath": filepath}, execution_conf)


class TuoniCommandUpload(TuoniDefaultPluginCommand):
    def __init__(self, filepath, data, execution_conf = None):
        super().__init__("upload", {"filepath": filepath}, execution_conf)
        self.files = {"file": ["filename.bin", data]}


class TuoniCommandCp(TuoniDefaultPluginCommand):
    def __init__(self, file_from, file_to, execution_conf = None):
        super().__init__("cp", {"from": file_from, "to": file_to}, execution_conf)


class TuoniCommandMv(TuoniDefaultPluginCommand):
    def __init__(self, file_from, file_to, execution_conf = None):
        super().__init__("mv", {"from": file_from, "to": file_to}, execution_conf)


class TuoniCommandMkdir(TuoniDefaultPluginCommand):
    def __init__(self, dirpath, execution_conf = None):
        super().__init__("mkdir", {"dirpath": dirpath}, execution_conf)


#########################
## Plugin NET commands
#########################

class TuoniCommandSocks5(TuoniDefaultPluginCommand):
    def __init__(self, port, execution_conf = None):
        super().__init__("socks5", {"port": port}, execution_conf)


class TuoniCommandConnectTcp(TuoniDefaultPluginCommand):
    def __init__(self, host, port, execution_conf = None):
        super().__init__("connect-tcp", {"host": host, "port": port}, execution_conf)

#########################
## Plugin OS commands
#########################


class TuoniCommandexecuteAssembly(TuoniDefaultPluginCommand):
    def __init__(self, executable, parameters, execution_conf = None):
        super().__init__("execute-assembly", {"parameters": parameters}, execution_conf)
        self.files = {"executable": ["filename.bin", executable]}


class TuoniCommandInject(TuoniDefaultPluginCommand):
    def __init__(self, shellcode, execution_conf = None):
        super().__init__("inject", {}, execution_conf)
        self.files = {"shellcode": ["filename.bin", shellcode]}


class TuoniCommandProcinfo(TuoniDefaultPluginCommand):
    def __init__(self, execution_conf = None):
        super().__init__("procinfo", {}, execution_conf)


class TuoniCommandScreenshot(TuoniDefaultPluginCommand):
    def __init__(self, execution_conf = None):
        super().__init__("screenshot", {}, execution_conf)


class TuoniCommandSpawn(TuoniDefaultPluginCommand):
    def __init__(self, payloadId, encrypted_communication = True, execution_conf = None):
        super().__init__("spawn", {"payloadId": payloadId, "encryptedCommunication": encrypted_communication}, execution_conf)


class TuoniCommandJumpService(TuoniDefaultPluginCommand):
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, servicePath = None, serviceName = None, serviceDisplayName = None, cleanup = None, username = None, password = None, execution_conf = None):
        super().__init__("jump-service", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "servicePath":  servicePath, "serviceName":  serviceName, "serviceDisplayName":  serviceDisplayName, "cleanup":  cleanup, "username":  username, "password": password}, execution_conf)


class TuoniCommandJumpWinrm(TuoniDefaultPluginCommand):
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, executablePath = None, customPowershell = None, username = None, password = None, execution_conf = None):
        super().__init__("jump-winrm", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "executablePath":  executablePath, "customPowershell":  customPowershell, "username":  username, "password": password}, execution_conf)


class TuoniCommandJumpWmi(TuoniDefaultPluginCommand):
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, cmdline = None, username = None, password = None, execution_conf = None):
        super().__init__("jump-wmi", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "cmdline":  cmdline, "username":  username, "password": password}, execution_conf)


class TuoniCommandJumpSsh(TuoniDefaultPluginCommand):
    def __init__(self, payloadId = None, copyMethod = None, copyPath = None, target = None, cmdline = None, username = None, password = None, privateKeyPEM = None, privateKeyPassword = None, execution_conf = None):
        super().__init__("jump-wmi", {"payloadId":  payloadId, "copyMethod":  copyMethod, "copyPath":  copyPath, "target":  target, "cmdline":  cmdline, "username":  username, "password": password, "privateKeyPassword": privateKeyPassword}, execution_conf)
        self.files = {"privateKeyPEM": ["private.pem", privateKeyPEM]}

#########################
## Other commands
#########################
class TuoniCommandReverseShellCommunication(TuoniDefaultCommand):
    def __init__(self, input):
        super().__init__("cd", {"input": input})
        
