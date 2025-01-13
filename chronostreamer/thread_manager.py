import threading


class ThreadManager:
    def __init__(self):
        self.threads = {}

    def start_thread(self, name, target, args=()):
        if name in self.threads and self.threads[name].is_alive():
            print(f"Thread {name} is already running.")
            return
        thread = threading.Thread(target=target, args=args)
        self.threads[name] = thread
        thread.start()
        print(f"Started thread: {name}")

    def stop_thread(self, name):
        if name in self.threads:
            # Implement logic for stopping a thread gracefully.
            # Example: Setting a flag or using a stop mechanism in the target function.
            print(f"Stopped thread: {name}")
            self.threads.pop(name)
        else:
            print(f"Thread {name} not found.")

    def list_threads(self):
        active_threads = {name: thread.is_alive() for name, thread in self.threads.items()}
        return active_threads
