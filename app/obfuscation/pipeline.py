""" File: obfuscation/pipeline.py
Implements a Pipeline class for composing sequences of obfuscation 
transformation units, as well as storing and loading these
representations. """
from .. import interaction, settings as cfg
from ..debug import log
from .utils import ObfuscationUnit
from typing import Callable, Optional
import random, datetime, json


class Pipeline:
    """Represents the pipeline of transformations that will be applied to some C source code
    to produce an obfuscated program. Provides functionalities for altering this pipeline
    and processing source code."""

    def __init__(self, seed: int = None, *args) -> None:
        """Constructs a Pipeline object with the supplied random seed and transformations.

        Args:
            seed (int, optional): The seed to use for randomness in obfuscation. Defaults to None.
            *args: A variable number of obfuscation transformation units to use in the pipeline.
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)
        self.transforms = list(args)

    def add(self, transform: ObfuscationUnit, index: int = None) -> None:
        """Add a new obfuscation transform to the pipeline at the specified position.

        Args:
            transform (ObfuscationUnit): The transform to be added to the pipeline.
            index (int, optional): The position the transform will be inserted into the list.
            Defaults to None, which indicates the end of the pipeline.
        """
        if index is None:
            return self.transforms.append(transform)
        self.transforms = (
            self.transforms[:index] + [transform] + self.transforms[index:]
        )

    def print_progress(self, index: int, start_time: datetime.datetime) -> None:
        """Prints the current progress of the transformation pipeline to the standard
        output stream, displaying the progress through the entire pipeline as well as
        the next transformation to process.

        Args:
            index (int): The index of the last processed transform. If no transforms
                are yet processed, then this is intuitvely just -1.
            start_time (datetime): The start time of the pipeline processing."""
        time_passed = str(datetime.datetime.now() - start_time)
        if "." not in time_passed:
            time_passed += ".000000"
        max_transforms = len(self.transforms)
        status = str(index + 1)
        status = (len(str(max_transforms)) - len(status)) * "0" + status
        prog_percent = "({:.2f}%)".format(
            100 if max_transforms == 0 else (index + 1) / max_transforms * 100
        )
        prog_percent = (9 - len(prog_percent)) * " " + prog_percent
        if index < len(self.transforms) - 1:
            next_transform = self.transforms[index + 1]
            next_str = str(next_transform)
        else:
            next_str = ""
        print(f"{time_passed} - [{status}/{max_transforms}] {prog_percent} {next_str}")

    def process(self, source: interaction.CSource, progress_func: Callable | None = None) -> interaction.CSource | None:
        """Processes some C source code, applying all the pipeline's transformations in sequence
        to produce some output obfuscated C code.

        Args:
            source (interaction.CSource): The C source code to be obfuscated through the pipeline.

        Returns:
            Optional[interaction.CSource]: The resulting obfuscated C source code. Returns None on some error.
        """
        if source is None:
            return None
        if cfg.DISPLAY_PROGRESS:
            print(" ===Starting Obfuscation===")
            start_time = datetime.datetime.now()
            self.print_progress(-1, start_time)
        for i, t in enumerate(self.transforms):
            source = t.transform(source)
            if source is None:
                break
            if cfg.DISPLAY_PROGRESS:
                self.print_progress(i, start_time)
            if progress_func is not None:
                progress_func(i+1)
        return source

    def to_json(self) -> str:
        """Converts the pipeline of composed transformations to a serialised JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "seed": self.seed,
                "version": cfg.VERSION,
                "transformations": [t.to_json() for t in self.transforms],
            }
        )

    def from_json(json_str: str, use_gui: bool = False) -> Optional["Pipeline"]:
        """Converts the provided serialized JSON string to a transformation pipeline.

        Args:
            json_str (str): The JSON string to attempt to load.
            use_gui (bool): Defaults false - whether to load command line units (false) or
                GUI units (true).

        Returns:
            The corresponding Pipeline object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load composition file - supplied information is not valid JSON."
            )
            return None
        if "version" not in json_obj:
            log(
                "Failed to load composition file - supplied JSON contains no version field."
            )
            return None
        elif json_obj["version"] != cfg.VERSION:
            log(
                "Failed to load composition file - version mismatch. File is of version {}, running version {}".format(
                    json_obj["version"], cfg.VERSION
                )
            )
            return None
        if "seed" not in json_obj or json_obj["seed"] is None:
            seed = None
        elif not isinstance(json_obj["seed"], int):
            log(
                "Failed to load composition file - supplied seed is not a valid integer."
            )
            return None
        else:
            seed = json_obj["seed"]
        if "transformations" not in json_obj:
            json_transformations = []
        elif not isinstance(json_obj["transformations"], list):
            log(
                "Failed to load composition file - supplied transformation is not of list type."
            )
            return None
        else:
            json_transformations = json_obj["transformations"]
        transformations = []
        if use_gui:
            subc = ObfuscationUnit.__subclasses__()
            subclasses = []
            for class_ in subc:
                subclasses += class_.__subclasses__()
        else:
            subclasses = ObfuscationUnit.__subclasses__()
        for t in json_transformations:
            json_t = json.loads(t)
            if "type" not in json_t:
                log(
                    "Failed to load composition file - supplied transformation has no type.",
                    print_err=True,
                )
                return
            elif json_t["type"] not in [t.name for t in subclasses]:
                log(
                    "Failed to load composition file - supplied transformation type '{}' is invalid.".format(
                        json_t["type"]
                    ),
                    print_err=True,
                )
                return
            for transform in subclasses:
                if transform.name == json_t["type"]:
                    transformations.append(transform.from_json(t))
                    break
        return Pipeline(seed, *transformations)
