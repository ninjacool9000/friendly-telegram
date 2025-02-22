#    Friendly Telegram (telegram userbot)
#    Copyright (C) 2018-2019 The Authors

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json, asyncio, uuid

# Not thread safe
class Database():
    def __init__(self, backend):
        self._backend = backend
        self._pending = {}
        self._loading = True
    async def init(self):
        await self._backend.init(self.reload)
        db = await self._backend.do_download()
        if db != None:
            try:
                self._db = json.loads(db)
            except:
                # Don't worry if its corrupted. Just set it to {} and let it be fixed on next upload
                self._db = {}
        else:
            self._db = {}
        self._loading = False
    def get(self, owner, key, default=None):
        try:
            return self._db[owner][key]
        except KeyError:
            return default

    def set(self, owner, key, value):
        if self._loading:
            return
        self._db.setdefault(owner, {})[key] = value
        id = uuid.uuid4()
        task = asyncio.ensure_future(self._set(self._db, id))
        self._pending[id] = task
        return task

    async def _set(self, db, id):
        await self._backend.do_upload(json.dumps(db))
        del self._pending[id]

    async def reload(self, event):
        self._loading = True
        for task in self._pending:
            task.cancel()
        db = await self._backend.do_download()
