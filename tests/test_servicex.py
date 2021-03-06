import asyncio
from json import dumps, loads
import queue
import re
import shutil
from unittest import mock
from unittest.mock import MagicMock

from minio.error import ResponseError
import pandas as pd
import pytest

import servicex as fe


@pytest.fixture(scope="module")
def reduce_wait_time():
    old_value = fe.servicex.servicex_status_poll_time
    fe.servicex.servicex_status_poll_time = 0.01
    yield None
    fe.servicex.servicex_status_poll_time = old_value


class ClientSessionMocker:
    def __init__(self, text, status):
        self._text = text
        self.status = status

    async def text(self):
        return self._text

    async def json(self):
        return loads(self._text)

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


def good_copy(a, b, c):
    'Mock the fget_object from minio by copying out our test file'
    shutil.copy('tests/sample_servicex_output.root', c)


def make_minio_file(fname):
    r = mock.MagicMock()
    r.object_name = fname
    return r


@pytest.fixture()
def files_back_1(mocker):
    # I attempted a full blown mock, but it failed. It wasn't getting picked up.
    # No idea why. But I've left this here for future in case we return to it.
    # mock_minio = mocker.MagicMock(minio.api.Minio)
    # mocker.patch('minio.Minio', return_value=mock_minio)
    # mock_minio.list_objects = MagicMock(return_value=[make_minio_file('root:::dcache-atlas-xrootd-wan.desy.de:1094::pnfs:desy.de:atlas:dq2:atlaslocalgroupdisk:rucio:mc15_13TeV:8a:f1:DAOD_STDM3.05630052._000001.pool.root.198fbd841d0a28cb0d9dfa6340c890273-1.part.minio')])
    # mock_minio.fget_object = MagicMock(side_effect=good_copy)
    mocker.patch('minio.api.Minio.list_objects', return_value=[make_minio_file('root:::dcache-atlas-xrootd-wan.desy.de:1094::pnfs:desy.de:atlas:dq2:atlaslocalgroupdisk:rucio:mc15_13TeV:8a:f1:DAOD_STDM3.05630052._000001.pool.root.198fbd841d0a28cb0d9dfa6340c890273-1.part.minio')])
    mocker.patch('minio.api.Minio.fget_object', side_effect=good_copy)
    return None


@pytest.fixture()
def files_back_1_fail_initally(mocker):
    'Throw a response error - so the bucket doesn not get created right away'
    response = MagicMock()
    response.data = '<xml></xml>'
    mocker.patch('minio.api.Minio.list_objects', side_effect=[ResponseError(response, 'POST', 'Dude'), [make_minio_file('root:::dcache-atlas-xrootd-wan.desy.de:1094::pnfs:desy.de:atlas:dq2:atlaslocalgroupdisk:rucio:mc15_13TeV:8a:f1:DAOD_STDM3.05630052._000001.pool.root.198fbd841d0a28cb0d9dfa6340c890273-1.part.minio')]])
    mocker.patch('minio.api.Minio.fget_object', side_effect=good_copy)
    return None


@pytest.fixture()
def files_back_2(mocker):
    mocker.patch('minio.api.Minio.list_objects', return_value=[make_minio_file('root:::dcache-atlas-xrootd-wan.desy.de:1094::pnfs:desy.de:atlas:dq2:atlaslocalgroupdisk:rucio:mc15_13TeV:8a:f1:DAOD_STDM3.05630052._000001.pool.root.198fbd841d0a28cb0d9dfa6340c890273-1.part.minio'),
                                                               make_minio_file('root:::dcache-atlas-xrootd-wan.desy.de:1094::pnfs:desy.de:atlas:dq2:atlaslocalgroupdisk:rucio:mc15_13TeV:8a:f1:DAOD_STDM3.05630052._000002.pool.root.198fbd841d0a28cb0d9dfa6340c890273-1.part.minio')])
    mocker.patch('minio.api.Minio.fget_object', side_effect=good_copy)
    return None


@pytest.fixture()
def files_back_2_one_at_a_time(mocker):
    q = queue.Queue()
    d = {}
    f1 = make_minio_file('root:::dcache-atlas-xrootd-wan.desy.de:1094::pnfs:desy.de:atlas:dq2:atlaslocalgroupdisk:rucio:mc15_13TeV:8a:f1:DAOD_STDM3.05630052._000001.pool.root.198fbd841d0a28cb0d9dfa6340c890273-1.part.minio')
    f2 = make_minio_file('root:::dcache-atlas-xrootd-wan.desy.de:1094::pnfs:desy.de:atlas:dq2:atlaslocalgroupdisk:rucio:mc15_13TeV:8a:f1:DAOD_STDM3.05630052._000002.pool.root.198fbd841d0a28cb0d9dfa6340c890273-1.part.minio')

    def return_files(req_id):
        if len(d) == 0:
            q.put("get-file-list 0")
            d['flag'] = True
            return [f1]
        else:
            q.put("get-file-list 1")
            return [f1, f2]

    def copy_files(a, b, c):
        q.put(f'copy-a-file {c}')
        good_copy(a, b, c)

    mocker.patch('minio.api.Minio.list_objects', side_effect=return_files)
    mocker.patch('minio.api.Minio.fget_object', side_effect=copy_files)
    return q


class list_objects_callable(mock.MagicMock):
    def __call__(self, *args, **kwargs):
        assert len(args) == 1
        req_id = args[0]
        num_files_s = req_id
        dash = req_id.find('_')
        if dash > 0:
            num_files_s = req_id[:dash]
        num_files = int(num_files_s)

        return [make_minio_file(f'root:::dcache-atlas-{req_id}-{i}') for i in range(0, num_files)]


@pytest.fixture()
def indexed_files_back(mocker):
    'Use the request id formatting to figure out how many files to deliver back'
    mocker.patch('minio.api.Minio.list_objects', new_callable=list_objects_callable)
    mocker.patch('minio.api.Minio.fget_object', side_effect=good_copy)


@pytest.fixture()
def good_transform_request(mocker):
    '''
    Setup to run a good transform request that returns a single file.
    '''
    called_json_data = {}

    def call_post(data_dict_to_save: dict, json=None):
        data_dict_to_save.update(json)
        return ClientSessionMocker(dumps({"request_id": "1234-4433-111-34-22-444"}), 200)
    mocker.patch('aiohttp.ClientSession.post', side_effect=lambda _, json: call_post(called_json_data, json=json))

    r2 = ClientSessionMocker(dumps({"files-remaining": "0", "files-processed": "1"}), 200)
    mocker.patch('aiohttp.ClientSession.get', return_value=r2)

    return called_json_data


@pytest.fixture()
def bad_transform_request(mocker):
    '''
    Fail when we return!
    '''
    r1 = ClientSessionMocker(dumps({"message": "Things Just Went Badly"}), 400)
    mocker.patch('aiohttp.ClientSession.post', return_value=r1)

    return None


@pytest.fixture()
def good_transform_request_delayed_finish(mocker):
    '''
    Setup to run a good transform request that returns a single file.
    '''
    r1 = ClientSessionMocker(dumps({"request_id": "1234-4433-111-34-22-444"}), 200)
    mocker.patch('aiohttp.ClientSession.post', return_value=r1)

    f1 = ClientSessionMocker(dumps({"files-remaining": "1", "files-processed": "1"}), 200)
    f2 = ClientSessionMocker(dumps({"files-remaining": "0", "files-processed": "2"}), 200)
    mocker.patch('aiohttp.ClientSession.get', side_effect=[f1, f2])

    return None


@pytest.fixture()
def good_requests_indexed(mocker):
    '''
    Parse the dataset to figure out what is to be done
    '''
    def call_post(_, json=None):
        dataset = json['did']
        info = re.search('^[a-z]+_([0-9]+)_([0-9]+)$', dataset)
        query_number = info[1]
        nfiles = info[2]
        return ClientSessionMocker(dumps({"request_id": f'{nfiles}_{query_number}'}), 200)
    mocker.patch('aiohttp.ClientSession.post', side_effect=call_post)

    # Now get back the returns, which are just going to always be the same.
    g1 = ClientSessionMocker(dumps({"files-remaining": "0", "files-processed": "4"}), 200)
    mocker.patch('aiohttp.ClientSession.get', return_value=g1)


@pytest.mark.asyncio
async def test_good_run_single_ds_1file_pandas(good_transform_request, reduce_wait_time, files_back_1):
    'Simple run with expected results'
    r = await fe.get_data_async('(valid qastle string)', 'one_ds')
    assert isinstance(r, pd.DataFrame)
    assert len(r) == 283458


@pytest.mark.asyncio
async def test_fails_bucket_lookup_at_first(good_transform_request, reduce_wait_time, files_back_1_fail_initally):
    'Simple run with expected results'
    r = await fe.get_data_async('(valid qastle string)', 'one_ds')
    assert isinstance(r, pd.DataFrame)
    assert len(r) == 283458


@pytest.mark.asyncio
async def test_good_run_single_ds_2file_pandas(good_transform_request, reduce_wait_time, files_back_2):
    'Simple run with expected results'
    r = await fe.get_data_async('(valid qastle string)', 'one_ds')
    assert isinstance(r, pd.DataFrame)
    assert len(r) == 283458*2


@pytest.mark.asyncio
async def test_good_run_single_ds_1file_awkward(good_transform_request, reduce_wait_time, files_back_1):
    'Simple run with expected results'
    r = await fe.get_data_async('(valid qastle string)', 'one_ds', data_type='awkward')
    assert isinstance(r, dict)
    assert len(r) == 1
    assert b'JetPt' in r
    assert len(r[b'JetPt']) == 283458


@pytest.mark.asyncio
async def test_good_run_single_ds_2file_awkward(good_transform_request, reduce_wait_time, files_back_2):
    'Simple run with expected results'
    r = await fe.get_data_async('(valid qastle string)', 'one_ds', data_type='awkward')
    assert isinstance(r, dict)
    assert len(r) == 1
    assert b'JetPt' in r
    assert len(r[b'JetPt']) == 283458*2


@pytest.mark.asyncio
async def test_2awkward_combined_correctly(good_transform_request, reduce_wait_time, files_back_2):
    'Simple run with expected results'
    r = await fe.get_data_async('(valid qastle string)', 'one_ds', data_type='awkward')

    # Test that what we pull down can correctly be used by uproot methods
    import uproot_methods
    arr = uproot_methods.TLorentzVectorArray.from_ptetaphi(r[b'JetPt'], r[b'JetPt'], r[b'JetPt'], r[b'JetPt'])
    assert len(arr) == 283458*2


@pytest.mark.asyncio
async def test_image_spec(good_transform_request, reduce_wait_time, files_back_1):
    'Simple run with expected results'
    await fe.get_data_async('(valid qastle string)', 'one_ds', image='fork-it-over:latest')
    called = good_transform_request
    assert called['image'] == 'fork-it-over:latest'


@pytest.mark.asyncio
async def test_servicex_rejects_transform_request(bad_transform_request, reduce_wait_time):
    'Simple run bomb during transform query'
    try:
        await fe.get_data_async('(valid qastle string)', 'one_ds')
        assert False
    except fe.ServiceX_Exception as se:
        # Make sure the code failure, 400, is in the string somewhere.
        assert str(se).find('400') >= 0
        return


@pytest.mark.asyncio
async def test_bad_datatype_request(good_transform_request, reduce_wait_time, files_back_1):
    'Simple run with expected results'

    try:
        await fe.get_data_async('(valid qastle string)', 'one_ds', data_type='forkme')
    except BaseException:
        return
    assert False


def test_good_run_single_ds_1file_noasync(good_transform_request, reduce_wait_time, files_back_1):
    'Simple run with expected results, but with the non-async version'
    r = fe.get_data('(valid qastle string)', 'one_ds')
    assert isinstance(r, pd.DataFrame)
    assert len(r) == 283458


def test_good_run_single_ds_1file_noasync_with_loop(good_transform_request, reduce_wait_time, files_back_1):
    'Async loop has been created for other reasons, and the non-async version still needs to work.'
    _ = asyncio.get_event_loop()
    r = fe.get_data('(valid qastle string)', 'one_ds')
    assert isinstance(r, pd.DataFrame)
    assert len(r) == 283458


def test_run_with_running_event_loop(good_transform_request, reduce_wait_time, files_back_1):
    async def doit():
        r = fe.get_data('(valid qastle string)', 'one_ds')
        assert isinstance(r, pd.DataFrame)
        assert len(r) == 283458
    loop = asyncio.get_event_loop()
    loop.run_until_complete(doit())


@pytest.mark.asyncio
async def test_run_with_four_queries(good_requests_indexed, reduce_wait_time, indexed_files_back):
    'Try to run four transform requests at same time. Make sure each retursn what we expect.'
    r1 = fe.get_data_async('(valid qastle string)', 'ds_0_1')
    r2 = fe.get_data_async('(valid qastle string)', 'ds_1_2')
    r3 = fe.get_data_async('(valid qastle string)', 'ds_2_3')
    r4 = fe.get_data_async('(valid qastle string)', 'ds_3_4')
    all_wait = await asyncio.gather(*[r1, r2, r3, r4])
    assert len(all_wait) == 4
    for cnt, r in enumerate(all_wait):
        assert isinstance(r, pd.DataFrame)
        assert len(r) == 283458*(cnt+1)


@pytest.mark.asyncio
async def test_run_with_onehundred_queries(good_requests_indexed, reduce_wait_time, indexed_files_back):
    'Try to run four transform requests at same time. Make sure each retursn what we expect.'
    # Request 100 times, each with 1 file in the return.
    count = 100
    all_requests = [fe.get_data_async('(valid qastle string)', f'ds_{i}_1') for i in range(0, count)]
    all_wait = await asyncio.gather(*all_requests)
    assert len(all_wait) == count
    for cnt, r in enumerate(all_wait):
        assert isinstance(r, pd.DataFrame)
        assert len(r) == 283458


@pytest.mark.asyncio
async def test_files_downloaded_ready_in_sequence(good_transform_request_delayed_finish, reduce_wait_time, files_back_2_one_at_a_time):
    'If one file finishes first, and later the second one finishes, make sure we get both the files.'
    #  fe.servicex.servicex_status_poll_time = 1.0

    r1 = fe.get_data_async('(valid qastle string)', 'ds_0_2')
    r = await r1
    assert isinstance(r, pd.DataFrame)
    assert len(r) == 283458*2


@pytest.mark.asyncio
async def test_files_downloading_is_interleaved(good_transform_request_delayed_finish, reduce_wait_time, files_back_2_one_at_a_time):
    'Make sure files start the download before the transform is done'
    #  fe.servicex.servicex_status_poll_time = 1.0

    r1 = fe.get_data_async('(valid qastle string)', 'ds_0_2')
    await r1

    q = files_back_2_one_at_a_time
    print(q.qsize())

    ordering = []
    while q.qsize() > 0:
        ordering.append(q.get(False))

    print(ordering)

    assert ordering[0] == 'get-file-list 0'
    assert ordering[1].startswith('copy-a-file')

# TODO:
# Other tests
#  Loose connection for a while after we submit the request
#  Don't have request to submit the request
#  Fail during download due to bad (temporary) connection.
