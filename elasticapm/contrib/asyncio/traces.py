#  BSD 3-Clause License
#
#  Copyright (c) 2019, Elasticsearch BV
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  * Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#  FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import functools
from types import TracebackType
from typing import Any, Awaitable, Callable, Optional, Type, TypeVar

from elasticapm.conf.constants import LABEL_RE
from elasticapm.traces import SpanType, capture_span, execution_context
from elasticapm.utils import get_name_from_func

FuncType = Callable[..., Awaitable[Any]]
_AnnotatedFunctionT = TypeVar("_AnnotatedFunctionT", bound=FuncType)


class async_capture_span(capture_span):
    def __call__(self, func: _AnnotatedFunctionT) -> _AnnotatedFunctionT:
        self.name = self.name or get_name_from_func(func)

        @functools.wraps(func)
        async def decorated(*args, **kwds):
            async with self:
                return await func(*args, **kwds)

        return decorated

    async def __aenter__(self) -> Optional[SpanType]:
        return self.handle_enter(False)

    async def __aexit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ):
        self.handle_exit(exc_type, exc_val, exc_tb)


async def set_context(data, key="custom"):
    """
    Asynchronous copy of elasticapm.traces.set_context().
    Attach contextual data to the current transaction and errors that happen during the current transaction.

    If the transaction is not sampled, this function becomes a no-op.

    :param data: a dictionary, or a callable that returns a dictionary
    :param key: the namespace for this data
    """
    transaction = execution_context.get_transaction()
    if not (transaction and transaction.is_sampled):
        return
    if callable(data):
        data = await data()

    # remove invalid characters from key names
    for k in list(data.keys()):
        if LABEL_RE.search(k):
            data[LABEL_RE.sub("_", k)] = data.pop(k)

    if key in transaction.context:
        transaction.context[key].update(data)
    else:
        transaction.context[key] = data
