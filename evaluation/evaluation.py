from difflib import SequenceMatcher
from conllu import parse


class Word:
    """
    This class represents a word with its different fields (id, form, etc.).
    It allows to get hashable dictionaries to make the alignment.
    An object of the class Word corresponds to a line in a CoNLL-U file.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        Parameters:
        **kwargs: Key-value pairs, keys being id, form, lemma, upos, xpos, feats,
        head, deprel, deps, and misc
        """
        self.__dict__ = kwargs
    
    def __str__(self):
        if 'form' in self.__dict__:
            return self.form
        return ''
    
    def __eq__(self, other):
        # I consider that two token are equal if they have the same form
        attr = 'form'
        if other is None:
            return self is None
        if self is None:
            return other is None
        if attr not in self.__dict__:
            return attr not in other.__dict__
        elif attr not in other.__dict__:
            return attr not in self.__dict__
        return self.form == other.form
    
    def __hash__(self):
        if 'form' in self.__dict__:
            return hash(self.form)
        return hash(None)



def extract_tokens(filename):
    """
    Extracts the tokens from a CoNLL-U file.

    Parameters:
    filename (str): Name of the CoNLL-U file.

    Returns:
    List of tokens, each token having a dictionary whose keys are form, 
    lemma, upos, xpos, etc.
    """
    res = []
    # IDs are changed so that every token have a unique ID for the whole corpus
    current_id = 1
    with open(filename, 'r', encoding='utf-8') as f:
        sentences = parse(f.read())
        for sentence in sentences:
            for token in sentence:
                w = Word(**token)
                if 'head' in w.__dict__:
                    # calculate the id difference between the word and its governor (except for the root of the sentence)
                    if w.head is not None and w.head != 0:
                        diff = w.head - w.id
                        # as the IDs are modified the head is modified as well
                        w.head = current_id + diff
                w.id = current_id
                res.append(w)
                current_id += 1
    return res

def get_alignment(pred, gold):
    """
    Returns the common part between two files.

    Parameters:
    pred (str): Path to the prediction file.
    gold (str): Path to the gold file.

    Returns:
    List of tuples, each tuple containing two tokens corresponding to the
    prediction file and the gold file.
    """
    matcher = SequenceMatcher(None, pred, gold, autojunk=False)
    aligned = []
    for diff in matcher.get_opcodes():
        edit, pred_lo, pred_hi, gold_lo, gold_hi = diff
        if edit == 'equal':
            aligned.extend(zip(pred[pred_lo:pred_hi], gold[gold_lo:gold_hi]))
    return aligned

def compute_tokenization_score(pred_file, gold_file):
    """
    Computes the tokenization score. It corresponds to the number of words
    that are correctly segmented divided by the total number of words
    in the gold file.

    Parameters:
    pred_file (str): Path to the prediction file.
    gold_file (str): Path to the gold file.

    Returns:
    Score for tokenization (between 0 and 1)
    """
    token_pred = extract_tokens(pred_file)
    token_gold = extract_tokens(gold_file)
    alignment = get_alignment(token_pred, token_gold)
    nb_correct = len(alignment)
    total = len(token_gold)
    return nb_correct / total

def compute_accuracy(pred_file, gold_file):
    """
    Computes the accuracy score. It corresponds to the number of words that have
    the correct part of speech divided by the number of words that are correctly aligned.

    Parameters:
    pred_file (str): Path to the prediction file.
    gold_file (str): Path to the gold file.

    Returns:
    Accuracy (between 0 and 1)
    """
    token_pred = extract_tokens(pred_file)
    token_gold = extract_tokens(gold_file)
    alignment = get_alignment(token_pred, token_gold)

    total = len(alignment)
    nb_correct = 0

    for word in alignment:
        pred_word = word[0]
        gold_word = word[1]
        
        # If the UPOS is not present in the gold data, the predicted UPOS is considered as correct
        gold_without_upos = gold_word.upos is None
        correct_upos = pred_word.upos is not None and pred_word.upos == gold_word.upos or gold_without_upos
        if correct_upos:
            nb_correct += 1

    return nb_correct / total

def get_head_from_id(tokens, token_id):
    """
    Gives the head of the governor of the token identified by token_id.

    Parameters:
    tokens (list): list of tokens represented by instances of the class Word
    token_id (int): identifier of the token

    Returns:
    Instance of the Word class, corresponding to the governor of the token identified by token_id.
    If there is no token whose id is token_id the function returns None. If the governor is the root
    it returns a Word containing only two attributes id = 0 and form = ''
    """
    for i, token in enumerate(tokens):
        if token.id == token_id:
            if 'head' not in token.__dict__ or token.head is None:
                return None
            # if there is no governor (ie. the governor is the root), I use a specific word whose ID
            # is 0 and whose form is an empty string
            if token.head == 0:
                return Word(**{'id': 0, 'form': ''})
            
            current_token = None
            if token.head < token.id:
                # if the head is before the token (in the CoNLL-U file) move left until the head 
                # is found
                index = i - 1
                current_token = tokens[index]
                while token.head < current_token.id:
                    index -= 1
                    current_token = tokens[index]
            elif token.head > token.id:
                # if the head is after the token (in the CoNLL-U file) move right until the head 
                # is found
                index = i + 1
                current_token = tokens[index]
                while token.head > current_token.id:
                    index += 1
                    current_token = tokens[index]
            if 'form' in current_token.__dict__:
                return current_token
    return None

def compute_uas_las(pred, gold):
    """
    Computes precision, recall and F1 for UAS and LAS.

    Parameters:
    pred: Path to the file containing the prediction data
    gold: Path to the file containing the gold data

    Returns:
    Dictionary containing precision, recall and F1 for UAS and LAS
    """
    # Extract tokens from files
    pred_tokens = extract_tokens(pred)
    gold_tokens = extract_tokens(gold)

    nb_correct_governor = 0
    nb_correct_governor_label = 0
    nb_total_pred_uas = 0
    nb_total_gold_uas = 0
    nb_total_pred_las = 0
    nb_total_gold_las = 0

    # Only the words that are correctly aligned are considered
    alignment = get_alignment(pred_tokens, gold_tokens)
    for align in alignment:
        # Check whether the governor and label are defined
        pred_exists_uas = 'head' in align[0].__dict__ and align[0].head is not None
        pred_exists_las = pred_exists_uas and 'deprel' in align[0].__dict__ and align[0].deprel is not None
        gold_exists_uas = 'head' in align[1].__dict__ and align[1].head is not None
        gold_exists_las = pred_exists_uas and 'deprel' in align[1].__dict__ and align[1].deprel is not None
        
        # Check whether the governor is correct
        correct_governor = get_head_from_id(pred_tokens, align[0].id) == get_head_from_id(gold_tokens, align[1].id)

        if pred_exists_uas:
            nb_total_pred_uas += 1
        if gold_exists_uas:
            nb_total_gold_uas += 1
        if pred_exists_uas and gold_exists_uas:
            if correct_governor:
                nb_correct_governor += 1

        if pred_exists_las:
            nb_total_pred_las += 1
        if gold_exists_las:
            nb_total_gold_las += 1
        if pred_exists_las and gold_exists_las and correct_governor and align[0].deprel == align[1].deprel:
            nb_correct_governor_label += 1

        
    results = dict()
    results['UAS precision'] = nb_correct_governor / nb_total_pred_uas
    results['UAS recall'] = nb_correct_governor / nb_total_gold_uas
    if results['UAS precision'] == 0 and results['UAS recall'] == 0:
        results['UAS'] = 0.0
    else:
        results['UAS'] = (2 * results['UAS precision'] * results['UAS recall'])/(results['UAS precision'] + results['UAS recall'])
        
    results['LAS precision'] = nb_correct_governor_label / nb_total_pred_las
    results['LAS recall'] = nb_correct_governor_label / nb_total_gold_las
    if results['LAS precision'] == 0 and results['LAS recall'] == 0:
        results['LAS'] = 0.0
    else:
        results['LAS'] = (2 * results['LAS precision'] * results['LAS recall'])/(results['LAS precision'] + results['LAS recall'])
    return results




def main():
    pred_file = './annot1.conllu'
    gold_file = './gold.conllu'
    print('Tokenization:', compute_tokenization_score(pred_file, gold_file))
    print('Tag:', compute_accuracy(pred_file, gold_file))
    result = compute_uas_las(pred_file, gold_file)
    for key, value in result.items():
        print('{}: {}'.format(key, value))
    
if __name__ == '__main__':
    main()
