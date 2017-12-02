import importlib
import inspect
import os
import pathlib


class PackageTree(object):
    """Represents a Package, including the Subpackages and Classes inside it.

    Subpackages and Classes can be called as attributes:
    {package}.{classname}
    {package}.{subpackage}.{classname}

    or by accessing internal dictionaries:
    {package}.classes[{classname}]()
    {package}.subpackages[{subpackage}].[{classname}]()

    Classes are initialized automatically when called as
     attributes, but not when called from a dictionary.

    Args:
        module - The module to import.
        root - The root package, relative to this package.
        directory - Directory where the package is located,
            relative to the current working directory.
    """
    def __init__(self, module, root=None, directory=None):
        self.module = module
        self.root = root
        directory = directory or ""
        self.directory = "{}/{}".format(directory, self.module)

        self.subpackages = {}
        self.classes = self.__import_classes()

        self._gather_subpackages()

    def __import_classes(self):
        """Imports a module, inspects the Classes in the modules,
        then returns a dictionary containing them.

        Returns:
            dict: Classes in the module.
        """
        imported_module = importlib.import_module(
            self.module, package=self.root
        )
        classes = inspect.getmembers(imported_module, inspect.isclass)
        return dict(classes)

    def __getattr__(self, attr):
        """When calling an attribute, if it does not already exist,
        check if it's an imported Subpackage or Class.
        If either is true, add attr as an attribute of this Container.

        Raises:
            AttributeError: If tried to get anything which is not
            a Container or Class in this Container.
        """
        found_subpackage = self.subpackages.get(attr)
        if found_subpackage is not None:
            setattr(self, attr, found_subpackage)
            return getattr(self, attr)

        found_class = self.classes.get(attr)
        if found_class is not None:
            setattr(self, attr, found_class())
            return getattr(self, attr)

        raise AttributeError(
            '{attr} is not an imported Subpackage or Class.'.format(
                **locals()
            )
        )

    def _gather_subpackages(self):
        """
        Search a specific folder and its subfolders for Class objects.
        The directory structure is used to build a hierarchy of
        nested Containers.

        If folder is a valid python module, import it,
        inspect it, and add all the classes inside it as attributes of
        a Container.

        Do this for all the subfolders, adding each as a
        child Container relative to the subfolder's root.
        """
        # Get all the subfolders of the root.
        root = pathlib.Path(self.directory)
        all_subfolders = [x for x in root.glob('**/')]

        # Folders that aren't packages should be ignored.
        allowed_folders = []
        for folder in all_subfolders:
            if '__init__.py' in os.listdir(folder):
                allowed_folders.append(folder)

        # The root path may appear in the list of paths.
        try:
            allowed_folders.remove(root)
        except ValueError:
            pass

        # If the root was a relative python path, split it into parts.
        root_parts = self.directory.split('/')

        for path in allowed_folders:
            parts = list(path.parts)
            for part in root_parts:
                parts.remove(part)

            parts = '.'.join(parts)

            child_container = PackageTree(
                module='.{}'.format(parts),
                root=self.module
            )

            # Add each subfolder as a child of this PackageTree.
            self.subpackages[path.name] = child_container
