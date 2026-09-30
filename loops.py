
data = [1,88,3,0,1,21,9,8,2,3]
unique_data = []

for number in data:
    if number not in unique_data:
        unique_data.append(number)

for d in range(len(unique_data)):
    for i in range(1, len(unique_data)):
        if unique_data[i] < unique_data[i-1]:
            unique_data[i], unique_data[i-1] = unique_data[i-1], unique_data[i]


print(unique_data)