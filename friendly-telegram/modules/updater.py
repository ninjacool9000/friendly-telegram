# -*- coding: future_fstrings -*-

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

from .. import loader, utils
import logging, os, sys, atexit, asyncio, functools, random, git
from git import Repo

logger = logging.getLogger(__name__)

def register(cb):
    cb(UpdaterMod())


class UpdaterMod(loader.Module):
    """Updates itself"""
    def __init__(self):
        self.config = {"GIT_ORIGIN_URL": "https://github.com/penn5/friendly-telegram"}
        self.name = "Updater"

    async def restartcmd(self, message):
        """Restarts the userbot"""
        logger.debug(self._me)
        logger.debug(self.allclients)
        await message.edit('Restarting...')
        await self.restart_common(message)

    async def prerestart_common(self, message):
        logger.debug("Self-update. " + sys.executable + " -m " + utils.get_base_dir())
        await self._db.set(__name__, "selfupdatechat", utils.get_chat_id(message))
        await self._db.set(__name__, "selfupdatemsg", message.id)

    async def restart_common(self, message):
        await self.prerestart_common(message)
        atexit.register(restart)
        for client in self.allclients:
            # Terminate main loop of all running clients
            # Won't work if not all clients are ready
            if not client is message.client:
                await client.disconnect()
        await message.client.disconnect()

    async def downloadcmd(self, message):
        """Downloads userbot updates"""
        await message.edit("Downloading...")
        await self.download_common()
        await message.edit("Downloaded! Use <code>.restart</code> to restart.")

    async def download_common(self):
        try:
            repo = Repo(os.path.dirname(utils.get_base_dir()))
            origin = repo.remote("origin")
            origin.pull()
        except git.exc.InvalidGitRepositoryError:
            repo = Repo.init(os.path.dirname(utils.get_base_dir()))
            origin = repo.create_remote("origin", self.config["GIT_ORIGIN_URL"])
            origin.fetch()
            repo.create_head('master', origin.refs.master)
            repo.heads.master.set_tracking_branch(origin.refs.master)
            repo.heads.master.checkout(True)

    async def updatecmd(self, message):
        """Downloads userbot updates"""
        await message.edit("Downloading...")
        await self.download_common()
        await message.edit("Downloaded! Installation in progress.")
        heroku_key = os.environ.get("heroku_api_token")
        if heroku_key:
            from .. import heroku
            await self.prerestart_common(message)
            heroku.publish(self.allclients, heroku_key)
            self._db.set(__name__, "selfupdatechat", None)
            self._db.set(__name__, "selfupdatemsg", None)
            await message.edit("Already up-to-date!")
        else:
            await self.restart_common(message)

    async def client_ready(self, client, db):
        self._db = db
        self._me = await client.get_me()
        if db.get(__name__, "selfupdatechat") != None and db.get(__name__, "selfupdatemsg") != None:
            await self.update_complete(client)
        self._db.set(__name__, "selfupdatechat", None)
        self._db.set(__name__, "selfupdatemsg", None)

    async def update_complete(self, client):
        logger.debug("Self update successful! Edit message")
        heroku_key = os.environ.get("heroku_api_token")
        herokufail = ("DYNO" in os.environ) and (heroku_key is None)
        if herokufail:
            logger.warning("heroku token not set")
            msg = "Heroku API key is not set. Update was successful but updates will reset every time the bot restarts."
        else:
            logger.debug("Self update successful! Edit message: "+str(self.config))
            msg = "Restart successful!" if random.randint(0, 10) != 0 else "Restart failed successfully!"
        await client.edit_message(self._db.get(__name__, "selfupdatechat"), self._db.get(__name__, "selfupdatemsg"), msg)

def restart(*args):
    os.execl(sys.executable, sys.executable, "-m", os.path.relpath(utils.get_base_dir()), *args)
