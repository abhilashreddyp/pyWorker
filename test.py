#! python3

import threading

from time import sleep
from worker import Worker, Async, current, worker_pool


# Basic operations
print("thread operations: start/pause/resume/stop/join")
count = 0
def increaser(thread):
	global count

	@thread.listen("reset")
	def _(event):
		global count
		count = event.data

	while True:
		thread.wait(0.1)
		count += 1

thread = Worker(increaser).start()
sleep(0.55)
assert count == 5
thread.pause()
thread.fire("reset", 0)
sleep(0.15)
assert count == 0
thread.resume()
sleep(0.05)
assert count == 1
sleep(0.4)
assert count == 5
thread.stop()
sleep(0.15)
assert count == 5
thread.join()

print("stop parent thread will cause child to stop too")
parent = Worker()
child = Worker().parent(parent)
parent.start()
child.start()
parent.stop().join()
assert not parent.is_running()
assert not child.is_running()

print("main thread is not daemon thread")
thread = current()
assert not thread.is_daemon()

print("a thread is not daemon thread by the default")
thread = Worker().start()
assert not thread.is_daemon()

print("child thread will inherit default value from parent node")
child = Worker().parent(thread).start()
assert thread.is_daemon() == child.is_daemon()

print("parent should wait till none-daemon child thread stop")
thread.stop().join()
assert not child.is_running()

print("a thread will detached from parent on finished")
thread = current()
child = Worker().parent(thread).start()
child.stop()
thread.wait_event("CHILD_THREAD_END", target=child)
assert child not in thread.children

print("async task, let parent wait child")
thread = current()
def long_work(timeout):
	sleep(timeout)
	return "Finished in {} seconds".format(timeout)
async = thread.async(long_work, 0.1)
assert thread.await(async) == "Finished in 0.1 seconds"

print("async task, let child finished before getting")
async = thread.async(long_work, 0.1)
sleep(0.2)
assert thread.await(async) == "Finished in 0.1 seconds"

print("use Async class")
async = Async(long_work, 0.1)
assert async.get() == "Finished in 0.1 seconds"
async = Async(long_work, 0.1)
sleep(0.2)
assert async.get() == "Finished in 0.1 seconds"

print("Test bubble/broadcast message")
bubble = False
broadcast = False

parent = Worker()
@parent.listen("Some bubble event")
def _(event):
	global bubble
	bubble = True
	
child = Worker().parent(parent).start()
@child.listen("Some broadcast event")
def _(event):
	global broadcast
	broadcast = True
	
parent.start()
child.start()
	
child.fire("Some bubble event", bubble=True)
parent.fire("Some broadcast event", broadcast=True)

sleep(0.1)

assert bubble
assert broadcast

parent.stop()

print("starting as main will stack on current thread")
class MyWorker(Worker):
	def worker(self, param, hello=None):
		assert param == "Hello world!"
		assert hello == "Hello"
		assert current() is self
MyWorker().start_as_main("Hello world!", hello="Hello").join()

# The folowing tests relate to: http://stackoverflow.com/questions/3752618/python-adding-element-to-list-while-iterating
print("one-time listener")
thread = Worker().start()
@thread.listen("test")
def _(event):
	thread.unlisten(_)
thread.fire("test")

print("listener that add another listener")
@thread.listen("test2")
def _(event):
	def dummy(event):
		print("dummy")
	thread.listen("test2")(dummy)
thread.fire("test2")

thread.stop().join()

print("auto setup parent")
def parent(thread):
	child = Worker().start()
	assert child.parent_node == thread
Worker(parent).start().join()

print("only main thread is left")
assert len(worker_pool.pool) == 1
assert threading.active_count() == 1
