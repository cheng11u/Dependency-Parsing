def extract_annotations(conllu):
    """Extract for each token its governor and the label of the relation.

    Parameters:
    conllu (str): Input file in CoNLL-U format

    Returns:
    list(tuple): List of tuple containing for each tuple its governor and the 
    corresponding label
    """
    annots = []
    with open(conllu, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for l in lines:
            fields = l.split('\t')
            if len(fields) == 10:
                token_id = fields[0]
                if '-' not in token_id:
                    governor = fields[6]
                    label = fields[7]
                    annots.append((governor, label))
    return annots



def compute_uas_las(gold, annot):
    """Computes the UAS (Unlabelled attachment score) and LAS (Labelled 
    attachment score).
    
    Parameters:
    gold (list): List of tuples (governor, label) for the gold data
    annot (list): List of tuples (governor, label) for the annotation

    Returns:
    tuple: Tuple containing the UAS and LAS

    """
    nb_tokens = 0
    nb_correct_gov = 0
    nb_correct_gov_rel = 0
    gold_annot = extract_annotations(gold)
    file_annot = extract_annotations(annot)
    if len(gold_annot) == 0 or len(gold_annot) != len(file_annot):
        print('Cannot compute UAS and LAS')
        return False

    for i, ga in enumerate(gold_annot):
        nb_tokens += 1
        if ga[0] == file_annot[i][0]:
            nb_correct_gov += 1
            if ga[1] == file_annot[i][1]:
                nb_correct_gov_rel += 1

    uas = float(nb_correct_gov)/float(nb_tokens)
    las = float(nb_correct_gov_rel)/float(nb_tokens)
    return (uas, las)

if __name__ == '__main__':
    (uas, las) = compute_uas_las('./gold.conllu', './annot1.conllu')
    print('UAS = {}'.format(uas))
    print('LAS = {}'.format(las))