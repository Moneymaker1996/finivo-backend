from memory import store_memory, search_memory

print('Storing memory 1...')
store_memory(1, "User felt guilty after spending $700 on headphones.")
print('Storing memory 2...')
store_memory(1, "User usually avoids luxury purchases during weekdays.")

print('Searching for "headphones"...')
result1 = search_memory("headphones")
print('Result:', result1)

print('Searching for "luxury purchases"...')
result2 = search_memory("luxury purchases")
print('Result:', result2)
