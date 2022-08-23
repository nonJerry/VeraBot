from datetime import datetime as dtime
from datetime import timezone, timedelta
import logging
from typing import Any, List, Optional, overload
from dateutil.relativedelta import relativedelta
from pymongo.collection import Collection


class Member:

    def __init__(self, member_id: int, idol: str, last_membership: dtime, informed: bool, expiry_sent: bool):
        self.id = member_id
        self.idol = idol
        self.last_membership = last_membership
        self.informed = informed
        self.expiry_sent = expiry_sent

    def to_dict(self) -> dict:
        return {"id": self.id, "idol": self.idol, "last_membership" : self.last_membership, "informed": self.informed, "expiry_sent": self.expiry_sent}

    @staticmethod
    def create_member(data: dict) -> Optional['Member']:
        try:
            last_membership = data["last_membership"].replace(tzinfo = timezone.utc)
            if "idol" in data:
                idol = data["idol"]
            else:
                idol = None
            return Member(data["id"], idol, last_membership, data["informed"], data['expiry_sent'])
        except Exception:
            return
        

class ServerDatabase:

    def __init__(self, db_cluster, server_id : int):
        self.db = db_cluster[str(server_id)]
        self.server_id = server_id

    def _get_settings(self) -> Collection:
        return self.db["settings"]

    def __get_setting(self, setting_name: str) -> Any:
        return self._get_settings().find_one({'kind' : setting_name})['value']

    def __get_member_collection(self) -> Collection:
        return self.db['members']

    # getter settings

    def get_prefixes(self) -> List:
        return self._get_settings().find_one({'kind' : 'prefixes'})['values']
        
    def get_member_role(self) -> int:
        return self.__get_setting("member_role")

    def get_log_channel(self) -> int:
        return self.__get_setting("log_channel")

    def get_picture(self) -> str:
        return self.__get_setting("picture_link")

    def get_automatic(self) -> bool:
        return self.__get_setting("automatic_role")

    def get_additional_proof(self) -> bool:
        return self.__get_setting("require_additional_proof")

    def get_tolerance_duration(self) -> int:
        return self.__get_setting("tolerance_duration")

    def get_inform_duration(self) -> int:
        return self.__get_setting("inform_duration")

    def get_logging(self) -> bool:
        return self.__get_setting("logging")

    def get_threads_enabled(self) -> bool:
        return self.__get_setting("threads")

    def get_proof_channel(self) -> int:
        return self.__get_setting("proof_channel")

    # setter settings

    def __set_setting(self, setting_name: str, value) -> None:
        self._get_settings().update_one({'kind': setting_name}, {'$set': {'value': value}})

    def set_member_role(self, role_id: int):
        return self.__set_setting("member_role", role_id)

    def set_log_channel(self, channel_id: int):
        return self.__set_setting("log_channel", channel_id)

    def set_picture(self, link: str):
        return self.__set_setting("picture_link", link)

    def set_automatic(self, value: bool):
        return self.__set_setting("automatic_role", value)

    def set_additional_proof(self, value: bool):
        return self.__set_setting("require_additional_proof", value)

    def set_tolerance_duration(self, duration: int):
        return self.__set_setting("tolerance_duration", duration)

    def set_inform_duration(self, duration: int):
        return self.__set_setting("inform_duration", duration)

    def set_logging(self, value: bool):
        return self.__set_setting("logging", value)

    def set_proof_channel(self, channel_id: int):
        return self.__set_setting("proof_channel", channel_id)

    def set_threads_enabled(self, value: bool):
        return self.__set_setting("threads", value)

    def set_prefix(self, prefix: str):
        self._get_settings().update_one({"kind": "prefixes"}, {'$push': {'values': prefix}})

    def remove_prefix(self, prefix: str) -> int:
        """Removes the given prefix from the database
        
        Parameters
        ----------
        prefix: str
            The prefix that should be removed
        
        Returns
        -------
        int
            The Number of removed prefixes
        """

        return self._get_settings().update_one({"kind": "prefixes"}, {'$pull': {'values': prefix}}).matched_count

    # other getter

    def get_member(self, member_id: int) -> Optional[Member]:
        # ka wofür ich das wollte
        member = self.__get_member_collection().find_one({"id": member_id})
        if member:
            return Member.create_member(member)

    def get_members(self, only_expired=False) -> List[Member]:
        inform_duration = self.get_inform_duration()
        notify_date = dtime.now(tz = timezone.utc) - relativedelta(months=1) - timedelta(days=1) + timedelta(days=inform_duration)
        member_list = []
        
        for member in self.db['members'].find():
            member = Member.create_member(member)
            
            if member and member.last_membership <= notify_date or not only_expired:
                member_list.append(member)
        return member_list

    def get_member_multi(self, member_id: int, vtuber) -> Optional[Member]:
        # ka wofür ich das wollte
        member = self.__get_member_collection().find_one({"id": member_id, "idol": vtuber})
        if member:
            return Member.create_member(member)            

    def get_vtuber(self) -> str:
        return Database().get_vtuber(self.server_id)

    # functional

    def update_member(self, member_id, db_date):
        # Check if id exists
        target_membership = self.get_member(member_id)
        if not target_membership:
            logging.info("Creating new membership for %s on server %s with last membership: %s.", member_id, self.server_id, db_date)
            self.__get_member_collection().insert_one({
                "id": member_id,
                "last_membership": db_date,
                "informed": False,
                "expiry_sent": False
            })
        else:
            logging.info("Updating membership for %s on server %s with last membership: %s.", member_id, self.server_id, db_date)
            self.__get_member_collection().update_one({"id": member_id}, {"$set": { "informed": False, "expiry_sent": False}, "$max": {"last_membership": db_date}})

    @overload
    def remove_member(self, member: int) -> int:
        ...
    @overload
    def remove_member(self, member: Member) -> None:
        ...
    def remove_member(self, member):
        if isinstance(member, int):
            return self.__get_member_collection().delete_one({"id": member}).deleted_count
        # has to be Member
        self.__get_member_collection().delete_one(member.to_dict())

    def informed(self, member: Member) -> None:
        self.__get_member_collection().update_one(member.to_dict(), {"$set": {"informed": True}})
        member.informed = True

    def expiry_sent(self, member: Member) -> None:
        self.__get_member_collection().update_one(member.to_dict(), {"$set": {"expiry_sent": True}})
        member.expiry_sent = True

    # multi server

    
    def add_multi_talent(self, name: str, log_id: int, role_id: int):
        if not self.get_multi_talents():
            self._get_settings().insert_one({ "kind": "multi_server", "values": []})
        self._get_settings().update_one({"kind": "multi_server"},{'$push': {'values': {"idol": name.lower(), "log_channel": log_id, "role_id": role_id}}})


    def remove_multi_talent(self, name: str) -> Optional[bool]:
        if not self.get_multi_talents():
            return False
        if self._get_settings().update_one({"kind": "multi_server"},{'$pull': {'values': {"idol": name.lower()}}}).modified_count:
            return True
        return False
        
    
    def get_multi_talents(self) -> Optional[dict]:
        talent_settings = self._get_settings().find_one({'kind' : "multi_server"})
        if hasattr(talent_settings, 'values'):
            return talent_settings['values']

    def get_multi_talent_infos(self, name: str) -> Optional[dict]:
        if not self.get_multi_talents():
            return
        return self._get_settings().find_one({"kind": "multi_server"}, {'values' : { '$elemMatch': {'idol' : name.lower()}}})['values'][0]

    def get_multi_talent_log_channel(self, name: str) -> Optional[int]:
        infos = self.get_multi_talent_infos(name)
        if infos:
            return infos['log_channel']

    def get_multi_talent_role_from_name(self, name: str) -> Optional[int]:
        infos = self.get_multi_talent_infos(name)
        if infos:
            return infos['role_id']

    def update_member_multi(self, member_id, db_date, vtuber):
        # Check if id exists with vtuber
        target_membership = self.get_member_multi(member_id, vtuber)
        if not target_membership:
            logging.info("Creating new membership for %s to talent %s on server %s with last membership: %s.", member_id, vtuber, self.server_id, db_date)
            self.__get_member_collection().insert_one({
                "id": member_id,
                "idol": vtuber,
                "last_membership": db_date,
                "informed": False,
                "expiry_sent": False
            })
        else:
            logging.info("Updating membership for %s to talent %s on server %s with last membership: %s.", member_id, vtuber, self.server_id, db_date)
            self.__get_member_collection().update_one({"id": member_id, "idol": vtuber}, {"$set": { "informed": False, "expiry_sent": False}, "$max": {"last_membership": db_date}})

    @overload
    def remove_member_multi(self, member: int, vtuber) -> int:
        ...
    @overload
    def remove_member_multi(self, member: Member, vtuber) -> None:
        ...
    def remove_member_multi(self, member, vtuber):
        if isinstance(member, int):
            return self.__get_member_collection().delete_one({"id": member, "idol": vtuber}).deleted_count
        # has to be Member
        self.__get_member_collection().delete_one(member.to_dict())

    


    def create_new_setting(self, kind, value):
        """Create a new setting for this server

        Parameters
        ----------
        kind: str
            The name of the new setting
        value: Any
            Default value of the new setting (also decides datatype)
        
        """

        # Create base configuration
        json = { "kind": kind, "value" : value}
        self._get_settings().insert_one(json)


    def create_new_member_setting(self, kind: str, value):
        """Create a new setting for each member

        Parameters
        ----------
        kind: str
            The name of the new setting
        value: Any
            Default value of the new setting (also decides datatype)
        
        DOES NOT ADD CODE TO ADD THIS SETTING TO NEW MEMBERS!
        
        """

        for member in self.get_members():
            # Create base configuration
            self.__get_member_collection().update_one({"id": member['id']}, {"$set": {kind: value}})



class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Database(metaclass=Singleton):

    def __init__(self, db_cluster):
        self.db_cluster = db_cluster

    def list_database_names(self) -> List:
        return self.db_cluster.list_database_names()

    def get_server_db(self, server_id: int) -> ServerDatabase:
        return ServerDatabase(self.db_cluster, server_id)

    def __get_settings_db(self):
        return self.db_cluster["settings"]

    def _get_general_settings(self):
        return self.__get_settings_db()["general"]

    def get_last_checked(self) -> Optional[dtime]:
        return self._get_general_settings().find_one({"name": "member_check"}).get("last_checked", None)

    def set_last_checked(self, time: dtime):
        self._get_general_settings().update_one({"name": "member_check"}, {"$set": {"last_checked": time}})


    def get_vtuber_list(self) -> dict:
        return self._get_general_settings().find_one({'name': "supported_idols"})['supported_idols']

    def get_vtuber(self, server_id: int) -> str:
        settings_db = self._get_general_settings()
        result = settings_db.find_one({'name': 'supported_idols'}, {'supported_idols' : { '$elemMatch': {'guild_id' : server_id}}})

        if 'supported_idols' in result:
            return result['supported_idols'][0]['name'].title()
        else:
            logging.warn("Not supported server on getVtuber!")
            return "not supported server"

    def get_vtuber_guild(self, name: str) -> Optional[int]:
        result = self._get_general_settings().find_one({'name': 'supported_idols'}, {'supported_idols' : { '$elemMatch': {'name' : name.lower()}}})
        if 'supported_idols' in result:
            return result['supported_idols'][0]['guild_id']

    def set_vtuber(self, name: str, guild_id: int) -> None:
        logging.debug("Set VTuber in Database")
        settings = self._get_general_settings()
        # not already set for single talent servers
        if settings.find_one( { 'supported_idols.guild_id': guild_id}) and not guild_id in self.get_multi_server():
            settings.update_one({'supported_idols.guild_id': guild_id}, {'$set': {'supported_idols.$': {"name": name.lower(), "guild_id": guild_id}}})
        else:
            settings.update_one({"name": "supported_idols"}, {'$push': {'supported_idols': {"name": name.lower(), "guild_id": guild_id}}})

    def remove_vtuber(self, guild_id: int):
        self._get_general_settings().update_one({'name': 'supported_idols'}, {'$pull': { 'supported_idols': {'guild_id': guild_id}}})

    def remove_multi_talent_vtuber(self, guild_id: int, name: str):
        self._get_general_settings().update_one({'name': 'supported_idols'}, {'$pull': { 'supported_idols': {'name': name, 'guild_id': guild_id}}})

    def add_multi_server(self, guild_id: int):
        self._get_general_settings().update_one({"name": "multi_server"}, {'$push': {'ids': guild_id}})
        server_db = self.get_server_db(guild_id)
        set_vtuber = server_db.get_vtuber()
        if (set_vtuber != "not supported server"):
            server_db.add_multi_talent(set_vtuber, server_db.get_log_channel(), server_db.get_member_role())

    def remove_multi_server(self, guild_id: int):
        self._get_general_settings().update_one({'name': 'multi_server'}, {'$pull':  {'ids': guild_id}})
        server_db = self.get_server_db(guild_id)
        for _ in server_db.get_multi_talents():
            self.remove_vtuber(guild_id)
        server_db._get_settings().delete_one({'kind' : "multi_server"})

    def get_multi_server(self) -> list:
        return self._get_general_settings().find_one({'name': "multi_server"})['ids']


    def create_new_setting(self, kind, value):
        """Create a new setting for every server

        Parameters
        ----------
        kind: str
            The name of the new setting
        value: Any
            Default value of the new setting (also decides datatype)
        
        DOES NOT ADD CODE TO ADD THIS SETTING TO NEW SERVERS!
        
        """
        from utility import Utility

        dbnames = self.db_cluster.list_database_names()

        for server in dbnames:
            if Utility.is_integer(server):
                self.get_server_db(server).create_new_setting(kind, value)


    def create_new_member_setting(self, kind: str, value):
        """Create a new setting for every member of each server

        Parameters
        ----------
        kind: str
            The name of the new setting
        value: Any
            Default value of the new setting (also decides datatype)
        
        DOES NOT ADD CODE TO ADD THIS SETTING TO NEW MEMBERS!
        
        """

        from utility import Utility
        
        dbnames = self.db_cluster.list_database_names()

        for server in dbnames:
            if Utility.is_integer(server):
                self.get_server_db(server).create_new_member_setting(kind, value)

    

    def create_new_server(self, guild_id: int):
        dbnames = self.list_database_names()
    
        if not str(guild_id) in dbnames:
            new_guild_db = self.get_server_db(guild_id)

            # Create base configuration

            # default: $
            json = { "kind": "prefixes", "values" : ['$']}
            new_guild_db._get_settings().insert_one(json)

            # default: needs to be set
            new_guild_db.create_new_setting("member_role", 0)
            # default: needs to be set
            new_guild_db.create_new_setting("log_channel", 0)
            # default: no mod role
            new_guild_db.create_new_setting("mod_role", 0)
            # default: hololive logo
            new_guild_db.create_new_setting("picture_link","https://pbs.twimg.com/profile_images/1198438854841094144/y35Fe_Jj.jpg")
            # default: proof needs to be approved of first
            new_guild_db.create_new_setting("automatic_role", False)
            # default: no additional proof nececssary
            new_guild_db.create_new_setting("require_additional_proof", False)
            # default: role stays for one day after expiration
            new_guild_db.create_new_setting("tolerance_duration", 1)
            # default: notified one day before membership expires
            new_guild_db.create_new_setting("inform_duration", 1)
            # default: log messages (membership check) will be shown
            new_guild_db.create_new_setting("logging", True)
            # default: no thread per proof
            new_guild_db.create_new_setting("threads", False)
            # default: not necessary without actuated threads
            new_guild_db.create_new_setting("proof_channel", 0)
