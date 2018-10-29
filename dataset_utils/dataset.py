#! /usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals

import logging
import os
from abc import ABCMeta, abstractproperty, abstractmethod
from pathlib import Path

from utils import load_json, keep_only_utterances_with_audio

logger = logging.getLogger(__name__)


class Dataset(object):
    __metaclass__ = ABCMeta
    """
        Abstract dataset class to inherit from when implementing a new
        dataset handler
    """

    @classmethod
    @abstractmethod
    def from_dir(cls, dir):
        """
            Instantiates a dataset from a folder
        """
        raise NotImplementedError

    @abstractproperty
    def training_dataset(self):
        raise NotImplementedError

    @abstractproperty
    def test_dataset(self):
        raise NotImplementedError

    @abstractmethod
    def get_audio_file(self, text):
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, ex_type, value, traceback):
        pass


class TrainTestDataset(Dataset):
    """Interface for train/test metrics
    """

    def __init__(self, data_list, training_dataset, test_dataset):
        self.data = data_list
        self._training_dataset = training_dataset
        self._test_dataset = test_dataset
        self._normalized_training_dataset = None
        self._normalized_test_dataset = None
        self.language = self._training_dataset["language"]

        self.audio_corpus = {}
        for entry in self.data:
            text = entry['text']
            wav_file = entry['path_file']
            self.audio_corpus[text] = wav_file

        # clean up the dataset by removing utterances that don't have an audio
        self._test_dataset = keep_only_utterances_with_audio(
            self._test_dataset, self.audio_corpus
        )

    @classmethod
    def from_dir(cls, _dir):
        _dir = Path(_dir)
        metadata_path = _dir / "metadata.json"
        json_data = load_json(str(metadata_path))

        training_dataset_path = _dir / "training_dataset.json"
        training_dataset = load_json(str(training_dataset_path))

        test_dataset_path = _dir / "test_dataset.json"
        test_dataset = load_json(str(test_dataset_path))

        for entry in json_data:
            entry["path_file"] = str(_dir / entry["path_file"])

        return cls(json_data, training_dataset, test_dataset)

    def get_audio_file(self, text):
        wav = self.audio_corpus.get(text)
        if wav is None:
            raise KeyError("Text {} is absent from audio dataset".format(text))
        return wav

    @property
    def training_dataset(self):
        return self._training_dataset

    @property
    def test_dataset(self):
        return self._test_dataset


class CrossValDataset(Dataset):
    """Interface for cross validation metrics
    """

    def __init__(self, config, dataset, audio_corpus):
        self.config = config

        self.audio_corpus = {}
        for sentence, wav_file in audio_corpus.iteritems():
            self.audio_corpus[sentence] = wav_file

        # clean up the dataset by removing utterances that don't have an audio
        self._dataset = keep_only_utterances_with_audio(
            dataset, self.audio_corpus
        )

    @classmethod
    def from_dir(cls, _dir):
        config = load_json(os.path.join(_dir, "config.json"))
        dataset = load_json(os.path.join(_dir, config['dataset']))
        speech_corpus_dir = os.path.join(_dir, config['speech_corpus'])
        metadata = load_json(os.path.join(speech_corpus_dir, "metadata.json"))

        audio_corpus = {
            item['text']: os.path.abspath(
                os.path.join(speech_corpus_dir, 'audio', item['filename'])) for
            item in metadata.itervalues()
        }
        return cls(config, dataset, audio_corpus)

    def get_audio_file(self, text):
        wav = self.audio_corpus.get(text)
        if wav is None:
            raise KeyError("Text {} is absent from audio dataset".format(text))
        return wav

    @property
    def training_dataset(self):
        return self._dataset

    @property
    def test_dataset(self):
        raise TypeError(
            "CrossValDataset is not meant to be used with train test metrics"
        )
