

def sort_int(mylist: list[int]) -> list[int]:
    ret_list = mylist.copy()

    for i in range(len(ret_list)):
        for j in range(len(ret_list)):
            if ret_list[i] < ret_list[j]:
                ret_list[i], ret_list[j] = ret_list[j], ret_list[i]

        print(ret_list)

    return ret_list

sorted = sort_int

list1 = []
list2 = [0, 1]
list3 = [-1, 0, 2]
list4 = [2, 9, 14, 0, -2]
list5 = [15, 0, -1]

if (sorted(list1) == []):
    print("ok")

if (sorted(list2) == [0, 1]):
    print("ok")

if (sorted(list4) == [-2, 0, 2, 9, 14]):
    print("ok")


