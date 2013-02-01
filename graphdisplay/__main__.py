from protobuf import samples_pb2
from protobuf.samples_pb2 import sample_stream

from storageengine.storage import Session, Block

import os
import pylab
from uuid import UUID

#get session list
sessions = os.listdir("storage")

print("Available Sessions:")
i = 1
for folder in sessions:
    print("  %d. %s" % (i, folder))
    i += 1

#session chooser
session_dir = sessions[0]

session_index = open(os.path.join("storage", session_dir, "index"), "rb")
session = Session.deserialise(session_index.read())
session_index.close()

samples = session.query()

pylab.plot(samples)
pylab.grid()
pylab.show()