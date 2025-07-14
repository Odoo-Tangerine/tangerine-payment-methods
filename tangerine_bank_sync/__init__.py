from . import models

def _bank_post_init_hook(env):
    """Initialize bank information if not already present."""
    env['res.bank'].bank_information_sync()
