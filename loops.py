
data = [88,3,0,1,21,9,8,2,3]

for d in range(len(data)):
    for i in range(1,len(data)):
        if data[i] < data[i - 1]:
            if data[i] == data[i-1]:
                data[i]
            data[i], data[i - 1] = data[i - 1], data[i]

print(data)
