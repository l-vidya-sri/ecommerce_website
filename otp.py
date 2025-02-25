import random
def genotp():
    otp=''
    for i in range(2):
        otp=otp+random.choice([chr(i) for i in range(ord('A'),ord('Z')+1)])     #randomly choice the given list
        otp=otp+random.choice([chr(i) for i in range(ord('a'),ord('z')+1)])
        otp=otp+str(random.randint(0,9))
    print(otp)
    return otp