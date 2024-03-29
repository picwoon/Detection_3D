class SceneSamples():
    '''
    '''
    #---------------------------------------------------------------------------
    geo_def = ['2a07667f31f99fc450eaecc8fbd8aa46']
    #---------------------------------------------------------------------------
    paper_samples = ['0058113bdc8bee5f387bb5ad316d7b28']
    paper_samples_1  = ['00602d3d932a8d5305234360a9d1e0ad',  '0055398beb892233e0664d843eb451ca']
    paper_samples_2 = ['005f0859081006be329802f967623015', '007802a5b054a16a481a72bb3baca6a4','00922f91aa09dbdda3a74489ea0e21eb']
    # [200:300]
    paper_samples_3 = ['0173543a6c15604c28070aafa61868be'] + \
                    ['02164f84a9e7321f3071b2214df8c738', '0348a36dd0901c93081838056b111ed6'] + \
                    ['0348b9030a2ab02345e65ef28a1be6d2']

    paper_samples_4 = ['01b05d5581c18177f6e8444097d89db4', '01ef4e9bebeb6252257b2d48d3819630']
    paper_samples_5 = ['11535fb0648bb4634360fca94e95af23']

    #pcl_err = ['0d05b1c41404736ad97e7f7a4f4e7a0a', '02630c38db188f991a9db06bfece2bbd', '07dcb6099122622b5a5f49be798b6fb1', '0ef76f780f9514f9f2ce4f9ae2c3441c']
    pcl_err = ['29637ba3891da782b6461ac17f8b3706', '2a19b4d97c69232763f2406dab744757', '2aaf7d08e975b88ce3fa1277f43b912b']
    err_scenes = ['015d0e1cebc9475b8edb17b00b523f83'] + pcl_err
    #---------------------------------------------------------------------------
    # samples between [4K, 5K]
    occlusion = ['1e5b5abaf37672f31a68c64c86721e69']
    angle = ['1d51690abecf3d4d5fcb818a0721d23c', '1db62509ded045cbedfa7cd80fcfadba', '1deb63245dd9d06a5bbf1af2857049c4']+\
          ['280d53b7678ee5d7d6ee1cada764d4a3', '292815803989642a171d23d0cd7e3a7b']
    complex_structures = ['1d84d7ca97f9e05534bf408779406e30', '1d938aa8a23c8507e035f5a7d4614180','1dba3a1039c6ec1a3c141a1cb0ad0757', '1e694c1e4862169a5f153c8719887bfc','1e717bef798945693244d7702bb65605']
    parallel_close_wall_very_small_angle = ['1d997f4d7ab8ff946279c3cc48b9ac95']
    parallel_close_wall = ['1e1803ee618089e619878995307e3d4d', '1e7a7945cd9ce60ce43f47cb72f72286']
    extent_wall_small_angle = ['1de7aee49963c9f1b658ed5b0178e266']
    wall_window_close = ['1da8a8bda13441351fd933480f0fc819', '1e7a7945cd9ce60ce43f47cb72f72286']
    multi_windows_vertical = ['27e7978d19335c98323d377ce6688a5f', '284060d1077ae763243262612a831541', '28de6b671d96922c0059d4db81e00d5d']

    paper1_samples = occlusion + angle + complex_structures + parallel_close_wall_very_small_angle + parallel_close_wall + extent_wall_small_angle + wall_window_close

    intro = ['2a422d3b3d1efb94db2057db4aa95ad7', '2ac2a614bb98e22efb504ea1bcb89fc1']

    err_scenes += ['1da0456aa433300489e95a35f0f3cd9d', '1e3ed936ba615c69fe170e35cc1f6c41', '29249f38d5c95568795ab8713eea23b6', '2939fcd921cfe33bb657f87ad35a2d73', '29b884837db645baa306c2c7e7bd5106']+\
      ['29eab295c257844236e84ab8c805459c', '29efc6b3741fc57c63737e8f9b68f494', '2a4229d4567b6775ebbf9610973fc443', '2ac2a614bb98e22efb504ea1bcb89fc1']
    #---------------------------------------------------------------------------


    #---------------------------------------------------------------------------
    # good samples
    good_samples_complex = [ '0058113bdc8bee5f387bb5ad316d7b28','00922f91aa09dbdda3a74489ea0e21eb', '005f0859081006be329802f967623015', '007802a5b054a16a481a72bb3baca6a4','0b282337d087cd70ae60a822a1225130']
    paper0_samples = good_samples_complex[0:2] + ['0055398beb892233e0664d843eb451ca']
    #                                                           80a21c need cro pto view
    good_samples_angle = ['00602d3d932a8d5305234360a9d1e0ad', '0067620211b8e6459ff24ebe0780a21c', '02164f84a9e7321f3071b2214df8c738']

    # hard exampels: (1)
    hard_samples_long_wall = ['00466151039216eb333369aa60ea3efe']
    hard_samples_close_walls = ['001ef7e63573bd8fecf933f10fa4491b', '01b1f23268db0f2801f4685a7e1563b9', '0348b9030a2ab02345e65ef28a1be6d2']
    hard_samples_notwall_butsimilar = ['0016652bf7b3ec278d54e0ef94476eb8']
    hard_samples_window_wall_close = ['01b8fe9faef3a608714e93be9dc9fac1', '01ef4e9bebeb6252257b2d48d3819630', '0a8d5e4e15f7954c73f7d7ce71689363', '0ab0ccc66d87bd9a0996f66eefbc2399']
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

    big_size = ['2f3ae02201ad551e99870189e184af4f','015d0e1cebc9475b8edb17b00b523f83','2b9e5ffdd2bbec47905d56508e4daf9c','2659febc41e0436750d035ad38610c4c']
    super_big = ['2659febc41e0436750d035ad38610c4c']
    too_big = ['0cec4f261a11cb6d5e7518d695261b64', '0ff9275fa36108d69bbc53b941ef2497', '173c36eec78e89ca2459f2b7831cef45','2052749b9eea638fa90e31e86ba14821','23790b17761f655c7fdc38f7bdadaf95','247d0dc34e1d0cd54add57212cc938a0']+\
      ['256b04497f1fded640fd0ea0aaa6ebe2', '27b806ecfd19e1a2ff54ac951a1bc4f0', '2ea8d5543a9f32ef27f70c15b5006436','2f28208dbd74f65a535b917ea99661bf']

    #---------------------------------------------------------------------------

    bad_scenes_curved_walls = ['020179798688014a482f483e1a5debe5', '019853e4742f679151c34f2732c33c16', '1de4b3e04dc05c81ec9bf6a5ffe52252']+\
      ['27143c875575d97aa54cd686da3009f5', '109f1089527f1aa0ef7d8c1f79f863ed']

    # bad samples: not used in the training (1) BIM definition ambiguous
    bad_scenes_BIM_ambiguous = ['004e36a61e574321adc8da7b48c331f2', '00466151039216eb333369aa60ea3efe', '008969b6e13d18db3abc9d954cebe6a5', '0165e8534588c269219c9aafa9d888da']
    bad_scenes_raw_bad = ['0320272d1b3c30e2d9f897ff917cef15', '28986f682cec4d51f6e3f760d4780929']
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
      ['2593aef145a1f6c9b01e8511c961cad2', '28ae0e90b88bb2e909398654dc159ad9', '28bd5530205f031f5db74d5e7f5637df', '29b8d84fb0caad2ebcee0ec60eb09797', '2a80c6fa44d902d77054210b5330a58c', '2a8f2816180fd6a2a6f1811b6ed02c88', '2cd9ecd5c7a31c9583a398f7d581c0b2', '2e21cd462afdb055be9d4cd8408c33bb', '2e3827af5bebf864583c96224ef970c1', '2e5cf189c5348060c28f93305c02519e'] +\
      ['17fb6d544ef525adfa07af2e0b2455ef', '194a5a7b92a1c79cbe0492f2f73893ff', '00bd0753b017769050de40d757b8d603', '00d92cc9072fe4173a1e7778bbca118c','00e030e0e9198a0f9dd5389f2d2e9271', '0138ea33414267375b879ff7ccc1436c'] +\
      ['07dcc783a318e50156a252af4e922c43', '0efaa70a597665636b23fa1403b57905', '08a528bffa49ef69da42aa920a1b911b']

    bad_scenes = bad_scenes_curved_walls + bad_scenes_BIM_ambiguous + bad_scenes_raw_bad + err_scenes + bad_scenes_cannot_parse + too_big

    ceiling_bad_sampels = ['00aa93519f5d1a7747d69595cb9e7940','006ab253a81b9cd33ce8f94c6865af81','002ae037be8b7b7a8605866296c2d0a1','000cf80f9ff74db95a46cd3a269a6e7c', '0011725c3f4c57108aa17f90ed8bea54', '003ecdd4fe76e4421091094665f39c5a','0055398beb892233e0664d843eb451ca']
