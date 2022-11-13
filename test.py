import time
seconds = 5 #The amount of seconds i want the loop to execute 
end_time = time.time() + seconds
while time.time() < end_time:
    print("This loop will execute for 10 seconds")