from collections import deque, OrderedDict
from utils import Level

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
            self.report_hit('R' if operation == 'R' else 'W', address)
            if operation == 'W':
                self.dirty_bits[index].add(block_address)
            if self.eviction_policy == 'LRU':
                self.cache[index].move_to_end(tag)
            return 
        
        self.report_miss('R' if operation == 'R' else 'W', address)
        
        if self.higher_level:
            self.higher_level.access('R', address)
        else:
            self.report_hit('R', address)
        
        if len(self.cache[index]) >= self.associativity:
            self.evict(index)
        
        self.cache[index][tag] = block_address
        if operation == 'W':
            self.dirty_bits[index].add(block_address)

    def evict(self, cache_index):
        """
        Select a victim block in the given way provided this level's eviction policy. Calculate its block address and
        then invalidate said block.
        """
        # select a victim block in the set provided the eviction policy (FIFO | LRU | MRU)
        victim_block_tag = None  # todo

        if self.eviction_policy == 'FIFO':
            victim_block_tag, _ = self.cache[cache_index].popitem(last=False)
        elif self.eviction_policy == 'LRU':
            victim_block_tag, _ = self.cache[cache_index].popitem(last=False)
        elif self.eviction_policy == 'MRU':
            victim_block_tag, _ = self.cache[cache_index].popitem(last=True)

        # invalidate the block
        evicted_block = self._calculate_block_address_from_tag_index(victim_block_tag, cache_index)
        self.invalidate(evicted_block)

    def invalidate(self, block_address):
        """
        Invalidate the block given by block address. If the block is not in this level, then we know it is not in
        lower levels. If it is in this level, then we need to invalidate lower levels first since they may be dirty.
        Once all lower levels have been invalidated, we need to check if our level is dirty, and if it is, perform a
        writeback and report that. Finally, once all lower levels have been invalidated we can remove the block from
        our level and report the eviction.
        """
        index = self._calculate_index(block_address)
        tag = self._calculate_tag(block_address)

        if tag in self.cache[index]:
            del self.cache[index][tag]
            self.dirty_bits[index].discard(block_address)

