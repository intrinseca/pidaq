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
session = Session(UUID(session_dir))
block_files = os.listdir(os.path.join("storage", session_dir))

blocks = []
samples = []

for block_path in block_files:
    print(block_path)
    block_file = open(os.path.join("storage", session_dir, block_path), "rb")
    
    block = Block(0)
    block.deserialize(block_file.read(), session)
    blocks.append(block)
    
blocks = sorted(blocks, key = lambda x: x.timestamp)

for block in blocks:
    samples.extend(block.samples)

pylab.plot(samples)
pylab.grid()
pylab.show()