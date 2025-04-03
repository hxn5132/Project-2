from collections import deque, OrderedDict
from utils import Level
#
class CacheLevel(Level):
    def __init__(self, size, block_size, associativity, eviction_policy, write_policy, level_name, higher_level=None, lower_level=None):
        super().__init__(level_name, higher_level, lower_level)
        self.size = size
        self.block_size = block_size
        self.associativity = associativity
        self.eviction_policy = eviction_policy  # FIFO | LRU | MRU
        self.write_policy = write_policy  # always WB for this assignment

        self.num_sets = size // (block_size * associativity)
        self.cache = [OrderedDict() for _ in range(self.num_sets)]
        self.dirty_bits = [set() for _ in range(self.num_sets)]  # Tracks dirty blocks

    def _calculate_index(self, address):
        return (address // self.block_size) % self.num_sets

    def _calculate_tag(self, address):
        return (address // self.block_size) // self.num_sets

    def _calculate_block_address(self, address):
        return address - (address % self.block_size)

    def _calculate_block_address_from_tag_index(self, tag, cache_index):
        return (tag * self.num_sets + cache_index) * self.block_size

    def is_dirty(self, block_address):
        index = self._calculate_index(block_address)
        return block_address in self.dirty_bits[index]

    def access(self, operation, address):
        index = self._calculate_index(address)
        tag = self._calculate_tag(address)
        block_address = self._calculate_block_address(address)

        if tag in self.cache[index]:
            self.report_hit(operation, address)
            if operation == 'W':
                self.dirty_bits[index].add(block_address)
            if self.eviction_policy == 'LRU':
                self.cache[index].move_to_end(tag)
            return 

        self.report_miss(operation, address)

        if len(self.cache[index]) >= self.associativity:
            self.evict(index)

        if self.higher_level:
            self.higher_level.access('R', address)
        else:
            self.report_hit('R', address)

        self.cache[index][tag] = block_address
        if operation == 'W':
            self.dirty_bits[index].add(block_address)

    def evict(self, cache_index):
        if not self.cache[cache_index]:
            return

        victim_block_tag = None  

        if self.eviction_policy == 'FIFO' or self.eviction_policy == 'LRU':
            victim_block_tag, _ = self.cache[cache_index].popitem(last=False)
        elif self.eviction_policy == 'MRU':
            victim_block_tag, _ = self.cache[cache_index].popitem(last=True)

        victim_block_addr = self._calculate_block_address_from_tag_index(victim_block_tag, cache_index)

        if victim_block_addr in self.dirty_bits[cache_index]:
            self.report_writeback(victim_block_addr)
            if self.higher_level:
                self.higher_level.access('W', victim_block_addr)
            self.dirty_bits[cache_index].remove(victim_block_addr)

        self.report_eviction(victim_block_addr)

        if self.higher_level:
            self.higher_level.invalidate(victim_block_addr)

        self.invalidate(victim_block_addr)

    def invalidate(self, block_address):
        index = self._calculate_index(block_address)
        tag = self._calculate_tag(block_address)

        if tag in self.cache[index]:
            del self.cache[index][tag]
            self.dirty_bits[index].discard(block_address)
