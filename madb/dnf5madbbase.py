import libdnf5
import os
from datetime import datetime, timedelta
from libdnf5.common import QueryCmp_GLOB as GLOB
import madb.config as config


class Dnf5MadbBase():

    def __init__(self, release, arch, root, refresh=False):

        self.release = release
        self.arch = arch
        self.root = root

        # Create a new Base object
        self._base = libdnf5.base.Base()
        self._base_config = self._base.get_config()
        self._base_config.installroot = root
        # https://github.com/rpm-software-management/dnf5/issues/412#issuecomment-1493782078
        self._base_config.optional_metadata_types = ['filelists', 'other']
        self._base.setup()
        self._base.config_file_path = os.path.join(root, "dnf/dnf.conf")
        self._base.load_config()
        vars = self._base.get_vars().get()
        vars.set('releasever', release)
        vars.set('arch', arch)
        self._base_config.logdir = os.path.join(root, "dnf","logs")
        self._base_config.cachedir = os.path.join(root, "dnf", "cache")
        self._base_config.reposdir = os.path.join(root, "dnf", "etc","distro.repos.d")
        log_router = self._base.get_logger()
        logger = libdnf5.logger.create_file_logger(self._base)
        log_router.add_logger(logger)
        self._base_config.module_platform_id = f"Mageia:{release}"
        self._base_config.metadata_expire = 20 if refresh else -1
        self._repo_sack = self._base.get_repo_sack()
        repos = {}
        for section in ("core", "nonfree", "tainted"):
            for cl in ("backports", "backports_testing", "release", "updates", "updates_testing"):
                repo_name = f"{release}-{arch}-{section}-{cl}"
                repo_srpms_name = f"{release}-SRPMS-{section}-{cl}"
                repos[repo_name] = self._repo_sack.create_repo(repo_name)
                repos[repo_name].get_config().baseurl = os.path.join(config.MIRROR_URL, release, arch, "media", section, cl)
                repos[repo_name].get_config().name = f"{config.DISTRIBUTION[release]} {arch} {section.capitalize()} {cl.capitalize()}"
                repos[repo_srpms_name] = self._repo_sack.create_repo(repo_srpms_name)
                repos[repo_srpms_name].get_config().baseurl = os.path.join(config.MIRROR_URL, release, "SRPMS", section, cl)
                repos[repo_srpms_name].get_config().name = f"{config.DISTRIBUTION[release]} SRPMS {section.capitalize()} {cl.capitalize()}"
        self._repo_sack.update_and_load_enabled_repos(False)


    def search_name(self, values, graphical=False, repo=None):
        """Search in a list of package attributes for a list of keys.

        :param values: the values to match
        :return: a list of package objects
        """
        query = libdnf5.rpm.PackageQuery(self._base)
        #query.filter_arch([self.arch, "noarch"])
        query.filter_name(values, GLOB)
        if graphical:
            query.filter_file(["/usr/share/applications/*.desktop"], GLOB)
        if repo:
            query.filter_repo_id([repo], GLOB)
        return query

    def search_in_group(self, value, graphical=False, repo=None):
        """Search a list of package in a group.

        :param values: the values to match
        :return: a list of package objects
        """
        query = libdnf5.rpm.PackageQuery(self._base)
        query.filter_arch([self.arch, "noarch"])
        if graphical and graphical == "1":
            query.filter_file(["/usr/share/applications/*.desktop"], GLOB)
        if repo:
            query.filter_repo_id([repo])
        return [rpm for rpm in query if rpm.get_group().startswith(value)]

    def search_updates(self, backports=False, last=False, testing=True, graphical=False):
        query = libdnf5.rpm.PackageQuery(self._base)
        query.filter_arch([self.arch, "noarch"])
        if backports:
            repo = "*backports"
        else:
            repo = "*updates"
        if testing:
            repo += "_testing"
        query.filter_repo_id([repo], GLOB)
        if graphical:
            query.filter_file(["/usr/share/applications/*.desktop"], GLOB)
        if last:
            query.filter_recent(int((datetime.now() - timedelta(days=7)).timestamp()))
        return query

    def search_by_sources(self, values, repo=None):
        query = libdnf5.rpm.PackageQuery(self._base)
        query.filter_arch([self.arch, "noarch"])
        if repo:
            query.filter_repo_id([repo], GLOB)
        query.filter_sourcerpm(values, GLOB)
        return query

    def provides_requires(self, rpm_list):
        query = libdnf5.rpm.PackageQuery(self._base)
        query.filter_arch([self.arch, "noarch"])
        query.filter_repo_id([self.release + "*"], GLOB)
        query.filter_provides(rpm_list)
        return query

    def search_provides(self, rpm_list):
        query = libdnf5.rpm.PackageQuery(self._base)
        query.filter_arch([self.arch, "noarch"])
        query.filter_repo_id([self.release + "*"], GLOB)
        query.filter_provides(rpm_list)
        return query

    def search(self, search_type, search_list):
        query = libdnf5.rpm.PackageQuery(self._base)
        query.filter_arch([self.arch, "noarch"])
        query.filter_repo_id([self.release + "*"], GLOB)
        #search_list = self.search_name(rpm_list)
        if search_type == "requires":
            query.filter_requires(search_list)
        elif search_type == "recommends":
            query.filter_recommends(search_list)
        elif search_type == "suggests":
            query.filter_suggests(search_list)
        elif search_type == "supplements":
            query.filter_supplements(search_list)
        elif search_type == "provides":
            query.filter_provides(search_list)
        return query


    def repo_enabled(self):
        query = libdnf5.repo.RepoQuery(self._base)
        query.filter_enabled(True)
        return query