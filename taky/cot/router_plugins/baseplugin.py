class RoutingPlugin:
    def __init__(self, router):
        self.router = router
        self.config()

    def pre_process(self, src, dst, event):
        raise NotImplementedError()

    def pre_send(self, src, dst, event):
        raise NotImplementedError()

    def config(self):
        pass
