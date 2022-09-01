#https://www.youtube.com/watch?v=GC50dexQsRo&ab_channel=TokyoEdtech

import pickle
from unicodedata import name

#create a list
names = ["Angus Young", "Malcolm Young", "Bon Scott"]

print("Original List")
print(names)

#SAVE LIST
pickle.dump(names, open("names.dat", "wb"))

#CHANGE
names.remove("Bon Scott")

print("Changed List")
print(names)

#Load the saved data
names = pickle.load(open("names.dat", "rb"))


print("Original List")
print(names)
