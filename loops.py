

data = [1,3,0,9,7]

for d in range(len(data)):
    if data[d] < data[d-1]:
        data[d], data[d-1] = data[d-1], data[d]
print(data)