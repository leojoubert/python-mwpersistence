r"""
``$ mwpersistence diffs2persistence -h``
::

    Generates token persistence information from JSON revision documents
    annotated with diff information (see `mwdiffs dump2diffs|revdocs2diffs`).

    This utility expects to be fed revision documents in as a page-partitioned
    chronological sequence so that diffs can be computed upon in order.

    This utility uses a processing 'window' to limit memory usage.  New
    revisions enter the head of the window and old revisions fall off the tail.
    Stats are generated at the tail of the window.

    ::
                               window
                          .------+------.

        revisions ========[=============]=============>

                        /                \
                    [tail]              [head]


    Usage:
        diffs2persistence (-h|--help)
        diffs2persistence [<input-file>...] --sunset=<date>
                          [--window=<revs>] [--revert-radius=<revs>]
                          [--keep-diff] [--threads=<num>] [--output=<path>]
                          [--compress=<type>] [--verbose] [--debug]

    Options:
        -h|--help               Prints this documentation
        <input-file>            The path a file containing page-partitioned
                                JSON revision documents with a 'diff' field to
                                process.
        --sunset=<date>         The date of the database dump we are generating
                                from.  This is used to apply a 'time visible'
                                statistic.  Expects %Y-%m-%dT%H:%M:%SZ".
                                [default: <now>]
        --window=<revs>         The size of the window of revisions from which
                                persistence data will be generated.
                                [default: 50]
        --revert-radius=<revs>  The number of revisions back that a revert can
                                reference. [default: 15]
        --keep-diff             Do not drop 'diff' field data from the json
                                blobs.
        --threads=<num>         If a collection of files are provided, how many
                                processor threads should be prepare?
                                [default: <cpu_count>]
        --output=<path>         Write output to a directory with one output
                                file per input path.  [default: <stdout>]
        --compress=<type>       If set, output written to the output-dir will
                                be compressed in this format. [default: bz2]
        --verbose               Print dots and stuff to stderr
        --debug                 Print debug logging to stderr.
"""
import logging
import sys
import time
from collections import deque
from itertools import groupby
import hashlib

import mwcli
import mwxml.utilities
from more_itertools import peekable
from mwtypes import Timestamp

from ..state import DiffState

logger = logging.getLogger(__name__)


def process_args(args):
    return {'window_size': int(args['--window']),
            'revert_radius': int(args['--revert-radius']),
            'sunset': Timestamp(args['--sunset'])
                      if args['--sunset'] != "<now>"
                      else Timestamp(time.time()),
            'keep_diff': bool(args['--keep-diff'])}


def _diffs2persistence(*args, keep_diff=False, **kwargs):
    keep_diff = bool(keep_diff)

    docs = diffs2persistence(*args, **kwargs)

    if not keep_diff:
        docs = drop_diff(docs)

    yield from docs


def drop_diff(rev_docs):
    for rev_doc in rev_docs:
        rev_doc.pop('diff', None)
        yield rev_doc


def diffs2persistence(rev_docs, window_size=50, revert_radius=15, sunset=None,
                      verbose=False):
    """
    Processes a sorted and page-partitioned sequence of revision documents into
    and adds a 'persistence' field to them containing statistics about how each
    token "added" in the revision persisted through future revisions.

    :Parameters:
        rev_docs : `iterable` ( `dict` )
            JSON documents of revision data containing a 'diff' field as
            generated by ``dump2diffs``.  It's assumed that rev_docs are
            partitioned by page and otherwise in chronological order.
        window_size : `int`
            The size of the window of revisions from which persistence data
            will be generated.
        revert_radius : `int`
            The number of revisions back that a revert can reference.
        sunset : :class:`mwtypes.Timestamp`
            The date of the database dump we are generating from.  This is
            used to apply a 'time visible' statistic.  If not set, now() will
            be assumed.
        keep_diff : `bool`
            Do not drop the `diff` field from the revision document after
            processing is complete.
        verbose : `bool`
            Prints out dots and stuff to stderr

    :Returns:
        A generator of rev_docs with a 'persistence' field containing
        statistics about individual tokens.
    """
    rev_docs = mwxml.utilities.normalize(rev_docs)
    window_size = int(window_size)
    revert_radius = int(revert_radius)
    sunset = Timestamp(sunset) if sunset is not None \
                               else Timestamp(time.time())

    # Group the docs by page
    page_docs = groupby(rev_docs, key=lambda d: d['page']['title'])

    for page_title, rev_docs in page_docs:

        if verbose:
            sys.stderr.write(page_title + ": ")

        # We need a look-ahead to know how long this revision was visible
        rev_docs = peekable(rev_docs)

        # The window allows us to manage memory
        window = deque(maxlen=window_size)

        # The state does the actual processing work
        state = DiffState(revert_radius=revert_radius)

        while rev_docs:
            rev_doc = next(rev_docs)
            next_doc = rev_docs.peek(None)
            
            # Safest to recalculate sha1
            rev_doc["sha1"] = sha1(bytes(text, 'utf8')).hexdigest()

            if next_doc is not None:
                seconds_visible = Timestamp(next_doc['timestamp']) - \
                                  Timestamp(rev_doc['timestamp'])
            else:
                seconds_visible = sunset - Timestamp(rev_doc['timestamp'])

            if seconds_visible < 0:
                logger.warn("Seconds visible {0} is less than zero."
                            .format(seconds_visible))
                seconds_visible = 0

            _, tokens_added, _ = \
                state.update_opdocs(rev_doc['sha1'], rev_doc['diff']['ops'],
                                    (rev_doc['user'], seconds_visible))

            if len(window) == window_size:
                # Time to start writing some stats
                old_doc, old_added = window[0]
                window.append((rev_doc, tokens_added))
                persistence = token_persistence(old_doc, old_added, window,
                                                None)
                old_doc['persistence'] = persistence
                yield old_doc
                if verbose:
                    sys.stderr.write(".")
                    sys.stderr.flush()
            else:
                window.append((rev_doc, tokens_added))

        while len(window) > 0:
            old_doc, old_added = window.popleft()
            persistence = token_persistence(old_doc, old_added, window, sunset)
            old_doc['persistence'] = persistence
            yield old_doc
            if verbose:
                sys.stderr.write("_")
                sys.stderr.flush()

        if verbose:
            sys.stderr.write("\n")


def token_persistence(rev_doc, tokens_added, window, sunset):

    if sunset is None:
        # Use the last revision in the window
        sunset = Timestamp(window[-1][0]['timestamp'])

    seconds_possible = max(sunset - Timestamp(rev_doc['timestamp']), 0)

    return {
        'revisions_processed': len(window),
        'non_self_processed': sum(rd['user'] != rev_doc['user']
                                  for rd, _ in window),
        'seconds_possible': seconds_possible,
        'tokens': [td for td in generate_token_docs(rev_doc, tokens_added)]
    }


def generate_token_docs(rev_doc, tokens_added):
    for token in tokens_added:
        yield {
            "text": str(token),
            "persisted": len(token.revisions) - 1,
            "non_self_persisted": sum(u != rev_doc['user']
                                      for u, _ in token.revisions),
            "seconds_visible": sum(sv for _, sv in token.revisions)
        }

streamer = mwcli.Streamer(
    __doc__,
    __name__,
    _diffs2persistence,
    process_args
)
main = streamer.main
