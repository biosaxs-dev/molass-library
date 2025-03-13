"""
DataUtils.UvFileTrimming.py
"""
from molass_legacy.SerialAnalyzer.SerialDataUtils import load_uv_file

def trim_uvfile(in_uvfile, uv_slices, trimmed_uvfile, debug=False):
    """Trim the UV file with the given trimming information"""
    if debug:
        print(f"Trimming UV file {in_uvfile} to {trimmed_uvfile}")
    
    ret_dict = load_uv_file(in_uvfile, return_dict=True)
    if debug:
        print("data.shape=", ret_dict['data'].shape)
        # print("col_header=", ret_dict['col_header'])
        print("comment_lines=", ret_dict['comment_lines'])
    
    data = ret_dict['data']
    wvector = data[:,0] 
    amatrix = data[:,1:]

    islice, jslice = uv_slices
    trimmed_wvector = wvector[islice]
    trimmed_amatrix = amatrix[islice,jslice]

    comment_lines = ret_dict['comment_lines']
    header = comment_lines[-2]  # note that the last line is ">>>>>>>>>>>>>> Data End <<<<<<<<<<<<"
    split_header = header.split( '\t' )
    col_header = split_header[0:-1]
    if debug:
        print("len(col_header)=", len(col_header))
        for j in [0, 1, 2, -2, -1]:
            print("col_header[%d]=" % j, col_header[j])
    
    start = jslice.start
    stop = jslice.stop
    trimmed_header = '\t'.join([''] + col_header[start+1:stop] + ['\n']) 
    with open(trimmed_uvfile, 'w', newline='\n') as f:
        f.write(''.join(comment_lines[0:-1]))
        f.write(trimmed_header)
        for i in range(len(trimmed_wvector)):
            f.write('\t'.join([str(x) for x in [trimmed_wvector[i]] + list(trimmed_amatrix[i,:])]) + '\n')
        f.write(comment_lines[-1])  # ">>>>>>>>>>>>>> Data End <<<<<<<<<<<<"