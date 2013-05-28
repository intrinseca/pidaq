from graphdisplay import plot_samples
from storageengine.storage import Session, BlockPool
import os
import pylab

#get session list
sessions = [s for s in os.listdir("storage") if s.startswith('index-')]

print("Available Sessions:")
i = 1
for folder in sessions:
    print("  %d. %s" % (i, folder))
    i += 1

#session chooser
session_index = sessions[2]

path = os.path.join(os.getcwd(), "storage")
session_index_file = open(os.path.join(path, session_index), "rb")
session = Session.deserialise(session_index_file.read())
session.block_pool = BlockPool(file_root=path, pool_size=10)
session_index_file.close()

pylab.hold(True)

for i in range(0,4):
    (true_start, samples) = session.query(channel=i)
    pylab.plot(samples)
    
pylab.grid()
pylab.show()
