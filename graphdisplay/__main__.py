from graphdisplay import plot_samples
from storageengine.storage import Session
import os


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

samples = session.query(start=25, end=125)

plot_samples(samples)