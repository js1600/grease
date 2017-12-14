from tgt_grease.core import GreaseContainer
from tgt_grease.core.Types import Command
from bson.objectid import ObjectId
from bson.errors import InvalidId
from tgt_grease.core import ImportTool


class BridgeCommand(object):
    """Methods for Cluster Administration

    Attributes:
        imp (ImportTool): Import Tool Instance

    """

    def __init__(self, ioc=None):
        if isinstance(ioc, GreaseContainer):
            self.ioc = ioc
        else:
            self.ioc = GreaseContainer()
        self.imp = ImportTool(self.ioc.getLogger())

    def action_register(self):
        """Ensures Registration of server

        Returns:
            bool: Registration status

        """
        self.ioc.getLogger().debug("Registration Requested")
        if self.ioc.ensureRegistration():
            print("Registration Complete!")
            self.ioc.getLogger().info("Registration Completed Successfully")
            return True
        else:
            print("Registration Failed!")
            self.ioc.getLogger().info("Registration Failed")
            return False

    def action_info(self, node=None, jobs=None, prototypeJobs=None):
        """Gets Node Information

        Args:
            node (str): MongoDB Object ID to get information about
            jobs (bool): If true then will retrieve jobs executed by this node
            prototypeJobs (bool): If true then prototype jobs will be printed as well

        Note:
            provide a node argument via the CLI --node=4390qwr2fvdew458239
        Note:
            provide a jobs argument via teh CLI --jobs
        Note:
            provide a prototype jobs argument via teh CLI --pJobs

        Returns:
            bool: If Info was found

        """
        if not self.ioc.ensureRegistration():
            self.ioc.getLogger().error("Server not registered with MongoDB")
            print("Unregistered servers cannot talk to the cluster")
            return False
        if node:
            try:
                server = self.ioc.getCollection('JobServer').find_one({'_id': ObjectId(str(node))})
            except InvalidId:
                print("Invalid ObjectID")
                self.ioc.getLogger().error("Invalid ObjectID passed to bridge info [{0}]".format(node))
                return False
            if server:
                serverId = dict(server).get('_id')
            else:
                self.ioc.getLogger().error("Failed to find server [{0}] in the database".format(node))
                return False
        else:
            serverId = self.ioc.getConfig().NodeIdentity
        server = self.ioc.getCollection('JobServer').find_one({'_id': ObjectId(str(serverId))})
        if server:
            server = dict(server)
            print("""
<<<<<<<<<<<<<< SERVER: {0} >>>>>>>>>>>>>>
Activation State: {1} Date: {2}
Jobs: {3}
Operating System: {4}
Prototypes: {5}
Execution Roles: {6}
            """.format(
                server.get('_id'),
                server.get('active'),
                server.get('activationTime'),
                server.get('jobs'),
                server.get('os'),
                server.get('prototypes'),
                server.get('roles'))
            )
            if jobs and prototypeJobs:
                print("======================= SOURCING =======================")
                for job in self.ioc.getCollection('SourceData').find({'grease_data.sourcing.server': ObjectId(serverId)}):
                    print("""
-------------------------------
Job: {0}
-------------------------------
                    """, job['_id'])
            if jobs and prototypeJobs:
                print("======================= DETECTION =======================")
                for job in self.ioc.getCollection('SourceData').find({'grease_data.detection.server': ObjectId(serverId)}):
                    print("""
-------------------------------
Job: {0}
Start Time: {1}
End Time: {2}
Context: {3}
-------------------------------
                    """.format(
                        job['_id'],
                        job['grease_data']['detection']['start'],
                        job['grease_data']['detection']['end'],
                        job['grease_data']['detection']['detection'])
                    )
            if jobs and prototypeJobs:
                print("======================= SCHEDULING =======================")
                for job in self.ioc.getCollection('SourceData').find({'grease_data.scheduling.server': ObjectId(serverId)}):
                    print("""
-------------------------------
Job: {0}
Start Time: {1}
End Time: {2}
-------------------------------
                    """.format(
                        job['_id'],
                        job['grease_data']['scheduling']['start'],
                        job['grease_data']['scheduling']['end'])
                    )
            if jobs:
                print("======================= EXECUTION =======================")
                for job in self.ioc.getCollection('SourceData').find({'grease_data.execution.server': ObjectId(serverId)}):
                    print("""
-------------------------------
Job: {0}
Assignment Time: {1}
Completed Time: {2}
Execution Success: {3}
Command Success: {4}
Failures: {5}
Return Data: {6}
-------------------------------
                    """.format(
                        job['_id'],
                        job['grease_data']['execution']['assignmentTime'],
                        job['grease_data']['execution']['completeTime'],
                        job['grease_data']['execution']['executionSuccess'],
                        job['grease_data']['execution']['commandSuccess'],
                        job['grease_data']['execution']['failures'],
                        job['grease_data']['execution']['returnData'])
                    )
            return True
        else:
            print("Unable to locate server")
            self.ioc.getLogger().error("Unable to load [{0}] server for information".format(serverId))
            return False

    def action_assign(self, prototype, node=None):
        """Assign prototypes to a node either local or remote

        Args:
            prototype (str): Prototype Job to assign
            node (str): MongoDB ObjectId of node to assign to, if not provided will default to the local node

        Returns:
            bool: If successful true else false

        """
        job = self.imp.load(str(prototype))
        if not job or not isinstance(job, Command):
            print("Cannot find prototype [{0}] to assign check search path!".format(prototype))
            self.ioc.getLogger().error("Cannot find prototype [{0}] to assign check search path!".format(prototype))
            return False
        # Cleanup job
        job.__del__()
        del job
        if node:
            try:
                server = self.ioc.getCollection('JobServer').find_one({'_id': ObjectId(str(node))})
            except InvalidId:
                print("Invalid ObjectID")
                self.ioc.getLogger().error("Invalid ObjectID passed to bridge info [{0}]".format(node))
                return False
            if server:
                serverId = dict(server).get('_id')
            else:
                self.ioc.getLogger().error("Failed to find server [{0}] in the database".format(node))
                return False
        else:
            serverId = self.ioc.getConfig().NodeIdentity
        updated = self.ioc.getCollection('JobServer').update_one(
            {'_id': ObjectId(serverId)},
            {
                '$push': {
                    'prototypes': prototype
                }
            }
        ).acknowledged
        if updated:
            print("Prototype Assigned")
            self.ioc.getLogger().info("Prototype [{0}] assigned to server [{1}]".format(prototype, serverId))
            return True
        else:
            print("Prototype Assignment Failed!")
            self.ioc.getLogger().info("Prototype [{0}] assignment failed to server [{1}]".format(prototype, serverId))
            return False

    def action_unassign(self, prototype, node=None):
        """Unassign prototypes to a node either local or remote

        Args:
            prototype (str): Prototype Job to unassign
            node (str): MongoDB ObjectId of node to unassign to, if not provided will default to the local node

        Returns:
            bool: If successful true else false

        """
        job = self.imp.load(str(prototype))
        if not job or not isinstance(job, Command):
            print("Cannot find prototype [{0}] to unassign check search path!".format(prototype))
            self.ioc.getLogger().error("Cannot find prototype [{0}] to unassign check search path!".format(prototype))
            return False
        # Cleanup job
        job.__del__()
        del job
        if node:
            try:
                server = self.ioc.getCollection('JobServer').find_one({'_id': ObjectId(str(node))})
            except InvalidId:
                print("Invalid ObjectID")
                self.ioc.getLogger().error("Invalid ObjectID passed to bridge info [{0}]".format(node))
                return False
            if server:
                serverId = dict(server).get('_id')
            else:
                self.ioc.getLogger().error("Failed to find server [{0}] in the database".format(node))
                return False
        else:
            serverId = self.ioc.getConfig().NodeIdentity
        updated = self.ioc.getCollection('JobServer').update_one(
            {'_id': ObjectId(serverId)},
            {
                '$pull': {
                    'prototypes': prototype
                }
            }
        ).acknowledged
        if updated:
            print("Prototype Assignment Removed")
            self.ioc.getLogger().info("Prototype [{0}] unassigned from server [{1}]".format(prototype, serverId))
            return True
        else:
            print("Prototype Unassignment Failed!")
            self.ioc.getLogger().info("Prototype [{0}] unassignment failed from server [{1}]".format(prototype, serverId))
            return False
