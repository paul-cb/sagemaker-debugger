from .save_config import SaveConfig, SaveConfigModes
from .utils import match_inc

class SaveManager:
  def __init__(self, collection_manager, include_collections_names,
               default_reduction_config,
               default_save_config):
    self.configs_for_collections = {}
    if isinstance(default_save_config, SaveConfig):
      sm = SaveConfigModes.create_simple_save_mode(default_save_config)
      self.default_save_modes = sm
    elif isinstance(default_save_config, SaveConfigModes):
      self.default_save_modes = default_save_config
    elif isinstance(default_save_config, dict):
      self.default_save_modes = SaveConfigModes(default_save_config)
    else:
      raise TypeError('save_config can only be a SaveConfig instance, or '
                      'a dictionary mapping from mode '
                      'to SaveConfig instance.')
    self.default_reduction_config = default_reduction_config
    self.collection_manager = collection_manager
    self.include_collections_names = include_collections_names
    self.save_collections = []
    self.save_states_cache = {}
    # todo clear cache for old steps
    self.tensor_to_collection = {}
    self.prepared = False

  def prepare(self):
    for c_name, c in self.collection_manager.get_collections().items():
      if self._should_collection_be_saved(c_name) \
        and c not in self.save_collections:
        self.save_collections.append(c)

    for c_name, c in self.collection_manager.get_collections().items():
      if c.save_config is not None:
        if isinstance(c.save_config, dict):
          self.configs_for_collections[c_name] = c.save_config
        elif isinstance(c.save_config, SaveConfig):
          sm = SaveConfigModes.create_simple_save_mode(c.save_config)
          self.configs_for_collections[c_name] = sm
        else:
          raise TypeError('collection {} has save config of wrong type {}'
                          .format(c_name, type(c.save_config)))
      else:
        self.configs_for_collections[c_name] = self.default_save_modes

      if c.reduction_config is None and self.default_reduction_config is not None:
        c.reduction_config = self.default_reduction_config
    self.prepared = True

  def _should_collection_be_saved(self, coll_name):
    return coll_name in self.include_collections_names

  def _raise_error(self):
    raise ValueError('Save Manager is not ready. '
                     'Please call prepare() method '
                     'before calling this method.')

  def get_all_collections_to_save(self):
    if not self.prepared:
      self._raise_error()
    return self.save_collections

  def collections_to_save(self, mode, step):
    if not self.prepared:
      self._raise_error()
    if (mode, step) not in self.save_states_cache:
      collection_save_state = {}
      for coll in self.save_collections:
        sm = self.configs_for_collections[coll.name]
        rv = sm.should_save_step(mode, step)
        if any(rv.values()):
          collection_save_state[coll.name] = rv
      self.save_states_cache[(mode, step)] = collection_save_state
    return self.save_states_cache[(mode, step)]

  def get_save_config(self, collection, mode):
    if not self.prepared:
      self._raise_error()
    return self.configs_for_collections[collection.name].get_save_config(mode)

  def get_reduction_config(self, collection):
    if not self.prepared:
      self._raise_error()
    return collection.get_reduction_config()

  def from_collections(self, tensor_name):
    # for tf this will be prepopulated because of prepare_tensors
    if not tensor_name in self.tensor_to_collection:
      # for mxnet it is computed and then cached
      matched_colls = []
      for coll in self.get_all_collections_to_save():
        if tensor_name in coll.tensor_names or \
         tensor_name in coll.reduction_tensor_names:
          # if being matched as reduction,
          # it must be in reduction_tensor_name, not with regex
          matched_colls.append(coll)
        elif match_inc(tensor_name, coll.get_include_regex()):
          if self.get_reduction_config(coll):
            coll.add_reduction_tensor_name(tensor_name)
          else:
            coll.add_tensor_name(tensor_name)
          matched_colls.append(coll)
      self.tensor_to_collection[tensor_name] = matched_colls
    return self.tensor_to_collection[tensor_name]

  def should_save_tensor(self, tensorname, mode, step):
    # returns dictionary with two keys:
    # if value for step is true in the dict, then we are saving this tensor
    # because we have hit the step to save this
    # if value for when_nan is true, we are considering saving this tensor
    # because this tensor might be saved if some other tensor is nan
    colls = self.from_collections(tensorname)
    final_ss = {'step': False, 'when_nan': False}
    ss_colls = self.collections_to_save(mode, step)
    for c in colls:
      if c.name in ss_colls:
        ss = ss_colls[c.name]
        final_ss['step'] = final_ss['step'] or ss['step']
        final_ss['when_nan'] = final_ss['when_nan'] or ss['when_nan']
    return final_ss