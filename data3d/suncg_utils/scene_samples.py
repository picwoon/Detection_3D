class SceneSamples():
    '''
    '''
    #---------------------------------------------------------------------------
    paper_samples = ['00602d3d932a8d5305234360a9d1e0ad', '0058113bdc8bee5f387bb5ad316d7b28', '0055398beb892233e0664d843eb451ca']
    paper_samples_0 = ['005f0859081006be329802f967623015', '007802a5b054a16a481a72bb3baca6a4','00922f91aa09dbdda3a74489ea0e21eb']
    # [200:300]
    paper_samples_1 = ['0173543a6c15604c28070aafa61868be'] + \
                    ['02164f84a9e7321f3071b2214df8c738', '0348a36dd0901c93081838056b111ed6'] + \
                    ['0348b9030a2ab02345e65ef28a1be6d2']

    paper_samples_2 = ['01b05d5581c18177f6e8444097d89db4', '01ef4e9bebeb6252257b2d48d3819630']
    paper_samples_3 = ['11535fb0648bb4634360fca94e95af23']

    #---------------------------------------------------------------------------
    err_scenes = []


    #---------------------------------------------------------------------------

    # good samples
    good_samples_complex = [ '0058113bdc8bee5f387bb5ad316d7b28', '005f0859081006be329802f967623015', '007802a5b054a16a481a72bb3baca6a4','00922f91aa09dbdda3a74489ea0e21eb']
    #                                                           80a21c need cro pto view
    good_samples_angle = ['00602d3d932a8d5305234360a9d1e0ad', '0067620211b8e6459ff24ebe0780a21c', '02164f84a9e7321f3071b2214df8c738']

    # hard exampels: (1)
    hard_samples_long_wall = ['00466151039216eb333369aa60ea3efe']
    hard_samples_close_walls = ['001ef7e63573bd8fecf933f10fa4491b', '01b1f23268db0f2801f4685a7e1563b9', '0348b9030a2ab02345e65ef28a1be6d2']
    hard_samples_notwall_butsimilar = ['0016652bf7b3ec278d54e0ef94476eb8']
    hard_samples_window_wall_close = ['01b8fe9faef3a608714e93be9dc9fac1', '01ef4e9bebeb6252257b2d48d3819630']
    hard_samples_short_wall = ['01b8fe9faef3a608714e93be9dc9fac1']
    hard_samplesmulti_win_vertical = ['02164f84a9e7321f3071b2214df8c738']


    # very hard
    very_hard_wall_window_close = ['0055398beb892233e0664d843eb451ca'] # a lot of windows are almost same with wall
    very_hard_windows_close = ['001e3c88f922f42b5a3f546def6eb83f']

    #---------------------------------------------------------------------------

    # hard and error_prone scenes
    hard_id1 = '001ef7e63573bd8fecf933f10fa4491b'  # two very close walls can easily be merged as one incorrectly (very hard to detect)
    hard_id3 = '002f987c1663f188c75997593133c28f'  # very small angle walls, ambiguous in wall definition
    hard_id4 = '00466151039216eb333369aa60ea3efe'  # too long wall
    hard_id5 = '004e36a61e574321adc8da7b48c331f2'  # complicated and wall definitoin ambiguous

    # hard to parse, but fixed already
    parse_hard_id0 = '0058113bdc8bee5f387bb5ad316d7b28'  # a wall is broken by no intersection

    #
    scene_id0 = '31a69e882e51c7c5dfdc0da464c3c02d' # 68 walls
    scene_id1 = '8c033357d15373f4079b1cecef0e065a' # one level, with yaw!=0, one wall left and right has angle (31 final walls)


    #---------------------------------------------------------------------------

    bad_scenes_curved_walls = ['020179798688014a482f483e1a5debe5', '019853e4742f679151c34f2732c33c16']

    # bad samples: not used in the training (1) BIM definition ambiguous
    bad_scenes_BIM_ambiguous = ['004e36a61e574321adc8da7b48c331f2', '00466151039216eb333369aa60ea3efe', '008969b6e13d18db3abc9d954cebe6a5', '0165e8534588c269219c9aafa9d888da']
    bad_scenes_raw_bad = ['0320272d1b3c30e2d9f897ff917cef15']
    # 0705e25aa6919af45268133bd2d98b65: no wall for window
    bad_scenes_cannot_parse_no_wall_for_window = ['13304f20f6327c21aa285069efb03ca1', '0705e25aa6919af45268133bd2d98b65', '142686fa469dda10dae66065be7961ef']
    bad_scenes_cannot_parse = bad_scenes_cannot_parse_no_wall_for_window +\
      ['032e05d444b03cc1c80c0700ad4238b1', '0382e82fab999376ef880fcff345090d'] + \
      ['100bcb702b28198108369345bf26f302', '1102fd6dc8702f1cd0f1f21508cce0bb', '110385ba3254a1816cc67a1b78243823'] +\
      ['14535bf081bd5ad2072683b43c8f0fd8', '14ab942f5f42112c1b2afa341b2b7522', '1515923b28f1cd8b101cc1f74358bb92'] +\
      ['09a4a9d37e1b6c909404f4cca86265f8'] +\
      ['09ca65c6876100d3e6db6d4114bde38c', '0a417c6459befd8a9fa4a5428f2de1e9', '0b3c558f26b1c066c5c5d851e2925b05', '0b79aa29e4b1dfdf3dd68345e298e907', '0bfd25a7d2af9c4dc539d452145d1370', '0c0a3b4e9e0a4a162cd627a291a858b6'] + \
      ['0c7a36399d3056631c2af4b131a37666', '0c88a0932fd1b91b72831de1550df84f', '0cd0e40be55719d4b223d69760fe95a6', '0d7c15290197e7ca90af9e206878bae2', '0e6e48390bf83d07b99b3a6b71797375', '0f0d7ba2b322cd7635a18c7f02f6168a'] + \
      ['161f617b86bc8388ca9f1bd2c805e0e9', '16322b525ce73f3d628eadec8800d58c', '17652ca3197dde089a16bb9fc1759114', '180c78c5f67d602cf9aa9936aace1ce9', '18468c7dc6cdd86a179bf13883e07dd8', '1948ad0c9782febf4ca10dd4c9fe4f63'] + \
      ['2593aef145a1f6c9b01e8511c961cad2', '28ae0e90b88bb2e909398654dc159ad9', '28bd5530205f031f5db74d5e7f5637df', '29b8d84fb0caad2ebcee0ec60eb09797', '2a80c6fa44d902d77054210b5330a58c', '2a8f2816180fd6a2a6f1811b6ed02c88', '2cd9ecd5c7a31c9583a398f7d581c0b2', '2e21cd462afdb055be9d4cd8408c33bb', '2e3827af5bebf864583c96224ef970c1', '2e5cf189c5348060c28f93305c02519e']

    bad_scenes = bad_scenes_curved_walls + bad_scenes_BIM_ambiguous + bad_scenes_raw_bad + err_scenes + bad_scenes_cannot_parse

