# xyz May 2019

def read_obj(fn):
    with open(fn, 'r') as f:
        lines = f.readlines()
    n = len(lines)

    #del_blocks = []
    find_end = 0
    lines_noceiling = []
    lines_ceiling = []
    for i in range(n):
        if find_end == 0 and  lines[i][0:9] == 'g Ceiling':
            del_start = i
            find_end = 1
        if find_end==1 and lines[i][0] !='g':
            find_end = 2
        if find_end == 2 and lines[i][0] =='g':
            del_end = i-1
            find_end = 0
            #del_blocks.append( (del_start, del_end) )

        if find_end == 2 and lines[i][0] == 'f':
            pass
        else:
            lines_noceiling.append(lines[i])

        if lines[i][0] == 'v' or  find_end >= 1:
            lines_ceiling.append(lines[i])

    #print(del_blocks)

    n_new = len(lines_noceiling)
    print(f'{n} -> {n_new}')

    new_fn = fn.replace('house.obj', 'no_ceiling_house.obj')
    with open(new_fn, 'w') as f:
        for l in lines_noceiling:
            f.write(l)
        print(f'write ok :\n {new_fn}')

    ceiling_fn = fn.replace('house.obj', 'ceiling.obj')
    with open(ceiling_fn, 'w') as f:
        for l in lines_ceiling:
            f.write(l)

if __name__ == '__main__':
    folder = '/home/z/SUNCG/suncg_v1/parsed'
    house_name = '31a69e882e51c7c5dfdc0da464c3c02d'
    house_name = '8c033357d15373f4079b1cecef0e065a'
    #house_name = 'b021ab18bb170a167d569dcfcaf58cd4'
    house_name = '0005b92a9ed6349df155a462947bfdfe'
    house_name = '0004d52d1aeeb8ae6de39d6bd993e992'
    fn = f'{folder}/{house_name}/house.obj'
    read_obj(fn)
