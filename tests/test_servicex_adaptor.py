from json import dumps
from servicex.servicex_adaptor import transform_status_stream, trap_servicex_failures
from typing import Optional

import aiohttp
import pytest

from servicex import ServiceXException, ServiceXUnknownRequestID, ServiceXAdaptor

from .utils_for_testing import ClientSessionMocker, short_status_poll_time, as_async_seq  # NOQA


# TODO: Nothing about the auth process is tested


@pytest.fixture
def servicex_status_request(mocker):
    '''
    Fixture that emulates the async python library get call when used with a status.

      - Does not check the incoming http address
      - Does not check the Returns a standard triple status from servicex
      - Does not check the headers
      - Call this to set:
            servicex_status_request(1, 2, 3)
            Sets remaining to 1, failed to 2, and processed to 3.
    '''
    files_remaining = None
    files_failed = None
    files_processed = 0

    def get_status(a, headers=None):
        r = {}

        def store(name: str, values: Optional[int]):
            nonlocal r
            if values is not None:
                r[name] = values
        store('files-remaining', files_remaining)
        store('files-skipped', files_failed)
        store('files-processed', files_processed)

        return ClientSessionMocker(dumps(r), 200)

    mocker.patch('aiohttp.ClientSession.get', side_effect=get_status)

    def set_it_up(remain: Optional[int], failed: Optional[int], processed: Optional[int]):
        nonlocal files_remaining, files_failed, files_processed
        files_remaining = remain
        files_failed = failed
        files_processed = processed

    return set_it_up


@pytest.fixture
def good_submit(mocker):
    client = mocker.MagicMock()
    r = ClientSessionMocker(dumps({'request_id': "111-222-333-444"}), 200)
    client.post = mocker.MagicMock(return_value=r)
    return client


@pytest.fixture
def bad_submit(mocker):
    client = mocker.MagicMock()
    r = ClientSessionMocker(dumps({'message': "bad text"}), 400)
    client.post = lambda d, json, headers: r
    return client


@pytest.fixture
def servicex_status_unknown(mocker):
    r = ClientSessionMocker(dumps({'message': "unknown status"}), 500)
    mocker.patch('aiohttp.ClientSession.get', return_value=r)


@pytest.mark.asyncio
async def test_status_no_login(servicex_status_request):

    servicex_status_request(None, 0, 10)
    sa = ServiceXAdaptor('http://localhost:500/sx')
    async with aiohttp.ClientSession() as client:
        r = await sa.get_transform_status(client, '123-123-123-444')
        assert len(r) == 3
        assert r[0] is None
        assert r[1] == 10
        assert r[2] == 0


@pytest.mark.asyncio
async def test_status_unknown_request(servicex_status_unknown):

    sa = ServiceXAdaptor('http://localhost:500/sx')
    with pytest.raises(ServiceXUnknownRequestID) as e:
        async with aiohttp.ClientSession() as client:
            await sa.get_transform_status(client, '123-123-123-444')

    assert 'transformation status' in str(e.value)


def version_mock(mocker, spec):
    import sys
    if sys.version_info[1] < 8:
        from asyncmock import AsyncMock  # type: ignore
        return AsyncMock(spec=spec)
    else:
        return mocker.MagicMock(spec=spec)


@pytest.mark.asyncio
async def test_status_stream_simple_sequence(mocker):
    adaptor = version_mock(mocker, spec=ServiceXAdaptor)
    adaptor.get_transform_status.configure_mock(return_value=(0, 1, 1))

    async with aiohttp.ClientSession() as client:
        v = [a async for a in transform_status_stream(adaptor, client, '123-455')]

    assert len(v) == 1
    assert v[0] == (0, 1, 1)


@pytest.mark.asyncio
async def test_status_stream_simple_2sequence(short_status_poll_time, mocker):
    adaptor = version_mock(mocker, spec=ServiceXAdaptor)
    adaptor.get_transform_status.configure_mock(side_effect=[(1, 1, 1), (0, 1, 1)])

    async with aiohttp.ClientSession() as client:
        v = [a async for a in transform_status_stream(adaptor, client, '123-455')]

    assert len(v) == 2
    assert v[0] == (1, 1, 1)
    assert v[1] == (0, 1, 1)


@pytest.mark.asyncio
async def test_watch_no_fail(short_status_poll_time, mocker):
    v = [a async for a in trap_servicex_failures(as_async_seq([(1, 0, 0), (0, 1, 0)]))]

    assert len(v) == 2
    assert v[0] == (1, 0, 0)
    assert v[1] == (0, 1, 0)


@pytest.mark.asyncio
async def test_watch_fail(short_status_poll_time, mocker):
    v = []
    with pytest.raises(ServiceXException) as e:
        async for a in trap_servicex_failures(as_async_seq([(1, 0, 0), (0, 0, 1)])):
            v.append(a)

    # Should force a failure as soon as it is detected.
    assert len(v) == 1
    assert 'failed to transform' in str(e.value)


@pytest.mark.asyncio
async def test_watch_fail_start(short_status_poll_time, mocker):
    v = []
    with pytest.raises(ServiceXException) as e:
        async for a in trap_servicex_failures(as_async_seq([(2, 0, 0), (1, 0, 1), (0, 1, 1)])):
            v.append(a)

    assert len(v) == 1
    assert 'failed to transform' in str(e.value)


@pytest.mark.asyncio
async def test_submit_good_no_login(good_submit):
    sa = ServiceXAdaptor(endpoint='http://localhost:5000/sx')

    rid = await sa.submit_query(good_submit, {'hi': 'there'})

    good_submit.post.assert_called_once()
    args, kwargs = good_submit.post.call_args

    assert len(args) == 1
    assert args[0] == 'http://localhost:5000/sx/servicex/transformation'

    assert len(kwargs) == 2
    assert 'headers' in kwargs
    assert len(kwargs['headers']) == 0

    assert 'json' in kwargs
    assert kwargs['json'] == {'hi': 'there'}

    assert rid is not None
    assert isinstance(rid, str)
    assert rid == '111-222-333-444'


@pytest.mark.asyncio
async def test_submit_bad(bad_submit):
    sa = ServiceXAdaptor(endpoint='http://localhost:5000/sx')

    with pytest.raises(ServiceXException) as e:
        await sa.submit_query(bad_submit, {'hi': 'there'})

    assert "bad text" in str(e.value)
