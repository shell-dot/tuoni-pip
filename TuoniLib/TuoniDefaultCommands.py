import base64

class TuoniDefaultCommand:
    def __init__(self, command_type, command_conf):
        self.command_type = command_type
        self.command_conf = command_conf
        self.execution_conf = None

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

class TuoniCommandBof(TuoniDefaultCommand):
    def __init__(self, bof_file, method, input):
        super().__init__("bof", {"bof_file": base64.b64encode(bof_file), "method": method, "input": input})


class TuoniCommandCd(TuoniDefaultCommand):
    def __init__(self, dir):
        super().__init__("cd", {"dir": dir})


class TuoniCommandCommandList(TuoniDefaultCommand):
    def __init__(self):
        super().__init__("commands-list", {})


class TuoniCommandDie(TuoniDefaultCommand):
    def __init__(self):
        super().__init__("die", {})


class TuoniCommandLs(TuoniDefaultCommand):
    def __init__(self, dir, depth):
        super().__init__("ls", {"dir": dir, "depth": depth})


class TuoniCommandTokenAdd(TuoniDefaultCommand):
    def __init__(self, pid):
        super().__init__("token-add", {"pid": pid})


class TuoniCommandTokenMake(TuoniDefaultCommand):
    def __init__(self, username, password):
        super().__init__("token-make", {"username": username, "password": password})


class TuoniCommandTokenList(TuoniDefaultCommand):
    def __init__(self):
        super().__init__("token-list", {})


class TuoniCommandTokenUser(TuoniDefaultCommand):
    def __init__(self, nr):
        super().__init__("token-use", {"nr": nr})


class TuoniCommandTokenDelete(TuoniDefaultCommand):
    def __init__(self, nr):
        super().__init__("token-del", {"nr": nr})


class TuoniCommandTokenDeleteAll(TuoniDefaultCommand):
    def __init__(self):
        super().__init__("token-del-all", {})


class TuoniCommandFileDelete(TuoniDefaultPluginCommand):
    def __init__(self, filepath, execution_conf = None):
        super().__init__("fs-delete", {"filepath": filepath}, execution_conf)


class TuoniCommandFileRead(TuoniDefaultPluginCommand):
    def __init__(self, filepath, execution_conf = None):
        super().__init__("fs-read", {"filepath": filepath}, execution_conf)


class TuoniCommandFileWrite(TuoniDefaultPluginCommand):
    def __init__(self, filepath, data, execution_conf = None):
        super().__init__("fs-write", {"filepath": filepath, "data": data}, execution_conf)


class TuoniCommandSocks5(TuoniDefaultPluginCommand):
    def __init__(self, port, execution_conf = None):
        super().__init__("socks5", {"port": port}, execution_conf)


class TuoniCommandCmd(TuoniDefaultPluginCommand):
    def __init__(self, command, execution_conf = None):
        super().__init__("cmd", {"command": command}, execution_conf)


class TuoniCommandExecAsm(TuoniDefaultPluginCommand):
    def __init__(self, executable, parameters, execution_conf = None):
        super().__init__("exec-asm", {"executable": executable, "parameters": parameters}, execution_conf)


class TuoniCommandInject(TuoniDefaultPluginCommand):
    def __init__(self, shellcode, execution_conf = None):
        super().__init__("inject", {"shellcode": shellcode}, execution_conf)


class TuoniCommandPowershell(TuoniDefaultPluginCommand):
    def __init__(self, command, execution_conf = None):
        super().__init__("powershell", {"command": command}, execution_conf)


class TuoniCommandProcinfo(TuoniDefaultPluginCommand):
    def __init__(self, execution_conf = None):
        super().__init__("procinfo", {}, execution_conf)


class TuoniCommandSpawn(TuoniDefaultPluginCommand):
    def __init__(self, listener_id, payload_type, encrypted_communication, execution_conf = None):
        super().__init__("spawn", {"listenerId": listener_id, "payloadType": payload_type, "encryptedCommunication": encrypted_communication}, execution_conf)


class TuoniCommandConnectTcp(TuoniDefaultPluginCommand):
    def __init__(self, host, port, execution_conf = None):
        super().__init__("connect-tcp", {"host": host, "port": port}, execution_conf)

