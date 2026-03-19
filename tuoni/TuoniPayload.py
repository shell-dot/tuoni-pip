class TuoniPayload:
    """
    A class that provides data and functionality for a sent payload.

    Attributes:
        payload_id (int): The unique identifier of the payload.
        template_id (str): The unique identifier of the payload template used to create the payload.
        template_name (str): The name of the payload template used to create the payload.
        configuration (dict): The configuration settings for the payload.
        listeners (list): The listeners associated with the payload.
        os (str): The operating system for the payload.
        architecture (str): The architecture for the payload.
        status (str): The status of the payload.
        encrypted_communication (bool): Indicates if the communication is encrypted.

    Examples:
        Create a payload from a conf dict and save it to disk:

        >>> payload = TuoniPayload(
        ...     conf={
        ...         "templateId": "shelldot.payload.windows-x64",
        ...         "configuration": {"type": "executable"}
        ...     },
        ...     c2=tuoni_c2
        ... )
        >>> payload.create(listener_id=1)
        >>> print(f"Created payload with ID: {payload.payload_id}")
        >>>
        >>> # Download and save the payload binary
        >>> data = payload.download()
        >>> with open("agent.exe", "wb") as f:
        ...     f.write(data)
        >>>
        >>> # Delete the payload when done
        >>> payload.delete()
    """

    def __init__(self, conf=None, c2=None):
        """
        Constructor for the payload class.

        Args:
            conf (dict): A dict to initialize the payload from. When passed a server
                response all fields are populated. When passed a user-provided creation
                dict, only ``templateId`` and ``configuration`` are required; ``name``,
                ``encryptedCommunication`` (default ``True``), and
                ``configurationFiles`` (default ``[]``) are optional.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.payload_id = None
        self.name = None
        self.template_id = None
        self.configuration = {}
        self.configuration_files = []
        self.encrypted_communication = True
        self.c2 = c2
        if conf is not None:
            self._load_conf(conf)

    def _load_conf(self, conf):
        self.payload_id = conf.get("id", None)
        self.name = conf.get("name", None)
        self.template_id = conf.get("templateId", self.template_id)
        self.configuration = conf.get("configuration", self.configuration)
        self.listeners = conf.get("listeners", [])
        self.os = conf.get("os", None)
        self.architecture = conf.get("architecture", None)
        self.status = conf.get("status", None)
        self.encrypted_communication = conf.get("encryptedCommunication", self.encrypted_communication)
        self.configuration_files = conf.get("configurationFiles", self.configuration_files)

    def load(self, id):
        """
        Load the payload data from the C2 server using the payload ID.

        Args:
            id (int): The unique identifier of the payload to load.
        """
        data = self.c2.request_get(f"/api/v1/payloads/{id}")
        self._load_conf(data)

    def create(self, listener_id):
        """
        Create the payload on the C2 server.

        Args:
            listener_id (int): The ID of the listener to associate with this payload.

        Examples:
            >>> payload = TuoniPayload(
            ...     conf={
            ...         "templateId": "shelldot.payload.windows-x64",
            ...         "configuration": {"type": "executable"}
            ...     },
            ...     c2=tuoni_c2
            ... )
            >>> payload.create(listener_id=1)
        """
        if self.payload_id is not None:
            raise Exception("Payload already created.")
        data = self.c2.request_post("/api/v1/payloads", {
            "payloadTemplateId": self.template_id,
            "name": self.name,
            "configuration": self.configuration,
            "configurationFiles": self.configuration_files,
            "listenerId": listener_id,
            "encrypted": self.encrypted_communication
        })
        self._load_conf(data)

    def delete(self):
        """
        Delete the payload from the C2 server.
        """
        if self.payload_id is None:
            raise Exception("Payload not created.")
        self.c2.request_delete(f"/api/v1/payloads/{self.payload_id}")
        self.payload_id = None

    def update(self):
        """
        Update the payload configuration on the C2 server.

        Args:
            new_configuration (dict): The new configuration settings for the payload.
        """
        if self.payload_id is None:
            raise Exception("Payload not created.")
        data = self.c2.request_patch(f"/api/v1/payloads/{self.payload_id}", {
            "name": self.name
        })
        self._load_conf(data)

    def download(self):
        """
        Download the payload from the C2 server.

        Returns:
            bytes: The binary data of the downloaded payload.
        """
        if self.payload_id is None:
            raise Exception("Payload not created.")
        return self.c2.request_get(f"/api/v1/payloads/{self.payload_id}/download", result_as_json=False, result_as_bytes=True)