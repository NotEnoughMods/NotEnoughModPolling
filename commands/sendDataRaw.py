ID = "raw"
permission = 3

def execute(self, name, params, channel, userdata, rank):
    self.send(" ".join(params), 4)