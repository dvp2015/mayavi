"""
Custom nodes for a Tree Editor that provide views for adding various nodes
to the tree.
"""
# Authors: Judah De Paula <judah@enthought.com>
#          Prabhu Ramachandran <prabhu_r@users.sf.net>
# Copyright (c) 2008, Enthought, Inc.
# License: BSD Style.

from textwrap import wrap
from os.path import join

from enthought.traits.api import (HasTraits, Str, Property, Any, Button,
                                  List, Instance, Bool, Dict,
                                  ToolbarButton)
from enthought.traits.ui.api import View, Item, Group, ListEditor, \
        ButtonEditor, TextEditor, TreeEditor, TreeNode
from enthought.traits.ui.table_column import ObjectColumn
from enthought.pyface.api import ImageResource
from enthought.resource.api import resource_path

from enthought.mayavi.core.registry import registry

image_path = join([resource_path, 'images'])

###############################################################################
class AdderNode(HasTraits):
    """ Base class that will display a TreeNode to add items to the tree.
    """
    
    # String to be shown in the TreeEditor.
    label = Str('Base AdderNode')
    
    # Default tooltip for this class.
    tooltip = Str('Add an item')
    
    # The parent object that should be manipulated for adding children.
    object =  Any
    
    # Duck-typing is necessary since Mayavi assumes nodes always have scenes.
    scene = Property

    # Trait view to show in the Mayavi current object panel.
    view = View(Group(label='AdderNode'))   

    def dialog_view(self):
        """ View shown by double-clicking on the node.  Same as in Base().
        """
        view = self.trait_view()    
        view.buttons = ['OK', ]
        view.title = self.label
        view.icon = ImageResource('add.ico')
        view.resizable = True
        view.width = 350
        view.height = 650
        return view
    
    def _get_scene(self):
        """ Trait Property getter for 'scene'.
        """
        object = self.obj
        if isinstance(object, AdderNode):
            return None
        if object is not None:
            return object.scene
        else:
            return None

###############################################################################
class SceneAdderNode(AdderNode):
    """ Subclass for adding Scene nodes to a Mayavi Engine node.
    """
    
    # String to be shown in the TreeEditor.
    label = Str('Add a new scene')
    
    # Button for the View.
    add_scene = Button('Add a new scene', 
                      image=ImageResource('add_scene.png'))  
    
    # Trait view to show in the Mayavi current object panel.
    view = View(Group(Item('add_scene', show_label=False, style='custom'), 
                      label='Add a scene'))
    
    
    def _add_scene_fired(self):
        """ Trait handler for when the add_scene button is clicked.
        """
        self.object.new_scene()


item_view = View(Item('add', style='custom',
                    show_label=False, enabled_when="enabled"),
                Item('documentation', style='readonly',
                    defined_when='enabled',
                    editor=TextEditor(multi_line=True),
                    resizable=True,
                    show_label=False),
                resizable=True,
                )

###############################################################################
class DocumentedItem(HasTraits):
    """ Container to hold a name and a documentation for an action.
    """

    # Whether the action is enabled
    enabled = Bool

    # Name of the action
    name = Str

    # Button to trigger the action
    add = ToolbarButton('Add', orientation='horizontal',
                    image=ImageResource('add.ico'))

    # Object the action will apply on
    object = Any

    # Two lines documentation for the action
    documentation = Str

    view = View(Item('add', style='custom', show_label=False),
                Item('documentation', style='custom', show_label=False,
                            resizable=True)) 
    
    def _add_fired(self):
        """ Trait handler for when the add_source button is clicked in
            one of the sub objects in the list.
        """
        action = getattr(self.object.menu_helper, self.id)
        action()


def documented_item_factory(name='', enabled=False, documentation='', 
                id='', object=None):
    """ Factory for creating a DocumentedItem with the right button
        label.
    """
    class MyDocumentedItem(DocumentedItem):
        add = ToolbarButton('%s' % name, orientation='horizontal',
                        image=ImageResource('add.ico'))

    return MyDocumentedItem(
                        name=name,
                        enabled=enabled,
                        documentation=documentation,
                        id=id,
                        object=object)


###############################################################################
class ListAdderNode(AdderNode):
    """ A node for adding object, with a list of objects to add generated
        from the registry.
    """

    # The list of items to display to the user.
    items_list = List(DocumentedItem)

    # A reference to the registry, to generate this list.
    items_list_source = List()

    # Selected item
    selected_item = Instance(DocumentedItem)

    self = Instance(AdderNode)

    def _self_default(self):
        return self

    def default_traits_view(self):
        nodes = [TreeNode(node_for=[AdderNode],
                          label='name',
                          copy=False,
                          delete=False,
                          rename=False,
                          children='items_list',
                          ), 
                 TreeNode(node_for=[DocumentedItem],
                          label='name',
                          copy=False,
                          delete=False,
                          rename=False,
                          icon_item='add.ico',
                          ), ]

        tree_editor = TreeEditor(editable=False,
                                 hide_root=True,
                                 orientation='vertical',
                                 selected='object.selected_item',
                                 nodes=nodes,
                                 )

        view = View(Item('self',
                            show_label=False,
                            editor=tree_editor,
                            resizable=True,
                            springy=True,
                            height=0.5),
                    Item('selected_item', style='custom', show_label=False,
                            height=0.5),
                    resizable=True)
        return view


    def _object_changed(self, value):
        """ Trait handler for when the self.object trait changes.
        """
        result = []
        if value is not None:
            # Don't need 'x', but do need to generate the actions.
            x = value.menu_helper.actions
            for src in self.items_list_source:
                name = src.menu_name.replace('&','')
                result.append(
                        documented_item_factory(
                                name=name,
                                enabled=self._is_action_suitable(value, src),
                                documentation=src.help,
                                id=src.id,
                                object=value)
                        )
        self.items_list = result


    def _is_action_suitable(self, object, src):
        """ Check that the action described by src can be applied on the
            given object.
        """
        if  hasattr(object.menu_helper, 'check_%s' % src.id) \
                and getattr(object.menu_helper, 'check_%s' % src.id)():
            return True
        else:
            return False


###############################################################################
class SourceAdderNode(ListAdderNode):
    """ Tree node that presents a view to the user to add a scene source.
    """

    # Button for adding a data file, with automatic format checking.
    open_file = Button('Load data from file')        
    
    # A reference to the registry, to generate this list.
    items_list_source = [source for source in registry.sources
                         if len(source.extensions) == 0]

    # The string to display on the icon in the TreeEditor.
    label = 'Add Data Source'
    
    # Trait view to show in the Mayavi current object panel.
    view = View(Group(Group(Item('open_file'),
                      show_labels=False, show_border=True),
                      Item('items_list', style='readonly',
                            editor=ListEditor(style='custom')),
                      show_labels=False,
                      label='Add a data source'))
   
    def _open_file_fired(self):
        """ Trait handler for when the open_file button is clicked.
        """
        self.object.menu_helper.open_file_action()

    def _is_action_suitable(self, object, src):
        return True

    
###############################################################################
class ModuleAdderNode(ListAdderNode):  
    """ Tree node that presents a view to the user to add modules.
    """
    
    # A reference to the registry, to generate this list.
    items_list_source = registry.modules

    def _object_changed(self, value):
        if value is not None:
            value.menu_helper._build_filter_actions()
        ListAdderNode._object_changed(self, value) 

###############################################################################
class FilterAdderNode(ListAdderNode):  
    """ Tree node that presents a view to the user to add filters.
    """
    
    # A reference to the registry, to generate this list.
    items_list_source = registry.filters


###############################################################################
class ModuleFilterAdderNode(AdderNode):  
    """ Tree node that presents a view to the user to add filter and
        modules.
    """
    
    # The string to display on the icon in the TreeEditor.
    label = 'Add module or filter'

    modules = Instance(ModuleAdderNode, ())

    filters = Instance(FilterAdderNode, ())

    def _object_changed(self):
        self.filters.object = self.object
        self.modules.object = self.object

    # Trait view to show in the Mayavi current object panel.
    view = View(
                Group(Item('modules', style='custom', springy=True,
                            resizable=True,
                            height=1.,
                            ), 
                    show_labels=False,
                    label='Visualization modules'),
                Group(Item('filters', style='custom', springy=True, 
                            resizable=True,
                            height=1.,
                            ), 
                    show_labels=False,
                    label='Processing filters'),
                )


### EOF #######################################################################
