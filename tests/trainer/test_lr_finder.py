import pytest
import torch

import tests.base.utils as tutils
from pytorch_lightning import Trainer
from pytorch_lightning.utilities.exceptions import MisconfigurationException
from tests.base import EvalModelTemplate


def test_error_on_more_than_1_optimizer(tmpdir):
    """ Check that error is thrown when more than 1 optimizer is passed """

    model = EvalModelTemplate()
    model.configure_optimizers = model.configure_optimizers__multiple_schedulers

    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        max_epochs=1
    )

    with pytest.raises(MisconfigurationException):
        trainer.lr_find(model)


def test_model_reset_correctly(tmpdir):
    """ Check that model weights are correctly reset after lr_find() """

    model = EvalModelTemplate()

    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        max_epochs=1
    )

    before_state_dict = model.state_dict()

    _ = trainer.lr_find(model, num_training=5)

    after_state_dict = model.state_dict()

    for key in before_state_dict.keys():
        assert torch.all(torch.eq(before_state_dict[key], after_state_dict[key])), \
            'Model was not reset correctly after learning rate finder'


def test_trainer_reset_correctly(tmpdir):
    """ Check that all trainer parameters are reset correctly after lr_find() """

    model = EvalModelTemplate()

    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        max_epochs=1
    )

    changed_attributes = ['callbacks', 'logger', 'max_steps', 'auto_lr_find',
                          'progress_bar_refresh_rate', 'early_stop_callback',
                          'accumulate_grad_batches', 'enable_early_stop',
                          'checkpoint_callback']
    attributes_before = {}
    for ca in changed_attributes:
        attributes_before[ca] = getattr(trainer, ca)

    _ = trainer.lr_find(model, num_training=5)

    attributes_after = {}
    for ca in changed_attributes:
        attributes_after[ca] = getattr(trainer, ca)

    for key in changed_attributes:
        assert attributes_before[key] == attributes_after[key], \
            f'Attribute {key} was not reset correctly after learning rate finder'


def test_trainer_arg_bool(tmpdir):
    """ Test that setting trainer arg to bool works """
    hparams = EvalModelTemplate.get_default_hparams()
    model = EvalModelTemplate(hparams)
    before_lr = hparams.learning_rate

    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        max_epochs=5,
        auto_lr_find=True
    )

    trainer.fit(model)
    after_lr = model.hparams.learning_rate
    assert before_lr != after_lr, \
        'Learning rate was not altered after running learning rate finder'


def test_trainer_arg_str(tmpdir):
    """ Test that setting trainer arg to string works """
    hparams = EvalModelTemplate.get_default_hparams()
    hparams.__dict__['my_fancy_lr'] = 1.0  # update with non-standard field
    model = EvalModelTemplate(hparams)

    before_lr = hparams.my_fancy_lr
    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        max_epochs=5,
        auto_lr_find='my_fancy_lr'
    )

    trainer.fit(model)
    after_lr = model.hparams.my_fancy_lr
    assert before_lr != after_lr, \
        'Learning rate was not altered after running learning rate finder'


def test_call_to_trainer_method(tmpdir):
    """ Test that directly calling the trainer method works """

    hparams = EvalModelTemplate.get_default_hparams()
    model = EvalModelTemplate(hparams)

    before_lr = hparams.learning_rate
    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        max_epochs=5,
    )

    lrfinder = trainer.lr_find(model, mode='linear')
    after_lr = lrfinder.suggestion()
    model.hparams.learning_rate = after_lr
    trainer.fit(model)

    assert before_lr != after_lr, \
        'Learning rate was not altered after running learning rate finder'


def test_accumulation_and_early_stopping(tmpdir):
    """ Test that early stopping of learning rate finder works, and that
        accumulation also works for this feature """

    hparams = EvalModelTemplate.get_default_hparams()
    model = EvalModelTemplate(hparams)

    before_lr = hparams.learning_rate
    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        accumulate_grad_batches=2
    )

    lrfinder = trainer.lr_find(model, early_stop_threshold=None)
    after_lr = lrfinder.suggestion()

    assert before_lr != after_lr, \
        'Learning rate was not altered after running learning rate finder'
    assert len(lrfinder.results['lr']) == 100, \
        'Early stopping for learning rate finder did not work'
    assert lrfinder._total_batch_idx == 100 * 2, \
        'Accumulation parameter did not work'


def test_suggestion_parameters_work(tmpdir):
    """ Test that default skipping does not alter results in basic case """

    hparams = EvalModelTemplate.get_default_hparams()
    model = EvalModelTemplate(hparams)

    # logger file to get meta
    trainer = Trainer(
        default_save_path=tmpdir,
        max_epochs=10,
    )

    lrfinder = trainer.lr_find(model)
    lr1 = lrfinder.suggestion(skip_begin=10)  # default
    lr2 = lrfinder.suggestion(skip_begin=80)  # way too high, should have an impact

    assert lr1 != lr2, \
        'Skipping parameter did not influence learning rate'
