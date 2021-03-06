# clean sequences after alignment, criteria based on sequences
# make inline with canonical ordering (no extra gaps)

import os, datetime, time, re
from scipy import stats
import numpy
from io_util import *

OUTGROUP = 'A/Beijing/32/1992'

def mask_from_outgroup(viruses):
	outgroup_seq = next(v for v in viruses if v['strain'] == OUTGROUP)['seq']
	for v in viruses:
		filtered = ""
		for (a, b) in zip(list(v['seq']), list(outgroup_seq)):
			if b != '-':
				filtered += str(a)
		v['seq'] = filtered

def clean_gaps(viruses):
	return [v for v in viruses if not '-' in v['seq']]

def clean_ambiguous(viruses):
	for virus in viruses:
		virus['seq'] = re.sub(r'[BDEFHIJKLMNOPQRSUVWXYZ]', '-', virus['seq'])

def date_from_virus(virus):
	return datetime.datetime.strptime(virus['date'], '%Y-%m-%d').date()

def times_from_outgroup(viruses):
	outgroup_date = date_from_virus(filter(lambda v: v['strain'] == OUTGROUP, viruses)[0])
	return map(lambda v: (date_from_virus(v) - outgroup_date).days, viruses)

def distance(seq_a, seq_b):
	dist = 0
	for (a, b) in zip(list(seq_a), list(seq_b)):
		if a != b:
			dist += 1
	return dist

def distances_from_outgroup(viruses):
	outgroup_seq = filter(lambda v: v['strain'] == OUTGROUP, viruses)[0]['seq']
	return map(lambda v: distance(outgroup_seq, v['seq']), viruses)

def clean_distances(viruses):
	times = times_from_outgroup(viruses)
	distances = distances_from_outgroup(viruses)
	slope, intercept, r_value, p_value, std_err = stats.linregress(times, distances)
	print "  slope: " + str(slope*365)
	print "  r: " + str(r_value)
	residuals = map(lambda t, d: (intercept + slope*t) - d, times, distances)
	r_sd = numpy.std(residuals)
	print "  residuals sd: " + str(r_sd)
	new_viruses = []
	for (v,r) in zip(viruses,residuals):		# filter viruses more than 5 sds up or down
		if (r > -5 * r_sd and r < 5 * r_sd) or v['strain'] == OUTGROUP:
			new_viruses.append(v)
	return new_viruses

def clean_outbreaks(viruses):
	"""Remove duplicate strains, where the geographic location, date of sampling and sequence are identical"""
	hash_to_count = {}
	new_viruses = []
	for v in viruses:
		geo = re.search(r'A/([^/]+)/', v['strain']).group(1)
		if geo:
			hash = geo + "_" + v['date'] + "_" + v['seq']
			if hash in hash_to_count:
				hash_to_count[hash] += 1
			else:
				hash_to_count[hash] = 1
				new_viruses.append(v)
	return new_viruses

def clean_reassortants(viruses):
	"""Remove viruses from the outbreak of triple reassortant pH1N1"""
	reassortant_seq = "ATGAAGACTATCATTGCTTTTAGCTGCATTTTATGTCTGATTTTCGCTCAAAAACTTCCCGGAAGTGACAACAGCATGGCAACGCTGTGCCTGGGACACCATGCAGTGCCAAACGGAACATTAGTGAAAACAATCACGGATGACCAAATTGAAGTGACTAATGCTACTGAGCTGGTCCAGAGTTCCTCAACAGGTGGAATATGCAACAGTCCTCACCAAATCCTTGATGGGAAAAATTGCACACTGATAGATGCTCTATTGGGGGACCCTCATTGTGATGACTTCCAAAACAAGGAATGGGACCTTTTTGTTGAACGAAGCACAGCCTACAGCAACTGTTACCCTTATTACGTGCCGGATTATGCCACCCTTAGATCATTAGTTGCCTCATCCGGCAACCTGGAATTTACCCAAGAAAGCTTCAATTGGACTGGAGTTGCTCAAGGCGGATCAAGCTATGCCTGCAGAAGGGGATCTGTTAACAGTTTCTTTAGTAGATTGAATTGGTTGTATAACTTGAATTACAAGTATCCAGAGCAGAACGTAACTATGCCAAACAATGACAAATTTGACAAATTGTACATTTGGGGGGTTCACCACCCGGGTACGGACAAGGACCAAACCAACCTATATGTCCAAGCATCAGGGAGAGTTATAGTCTCTACCAAAAGAAGCCAACAAACTGTAATCCCGAATATCGGGTCTAGACCCTGGGTAAGGGGTGTCTCCAGCATAATAAGCATCTATTGGACGATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCCCCTCGGGGTTACTTCAAAATACAAAGTGGGAAAAGCTCAATAATGAGATCAGATGCACACATTGATGAATGCAATTCTGAATGCATTACTCCAAATGGAAGCATTCCCAATGACAAACCTTTTCAAAATGTAAACAAGATCACATATGGAGCCTGTCCCAGATATGTTAAGCAAAACACCCTGAAATTGGCAACAGGAATGCGGAATGTACCAGAGAAACAAACTAGAGGCATATTCGGCGCAATTGCAGGTTTCATAGAAAATGGTTGGGAGGGAATGGTAGACGGTTGGTACGGTTTCAGGCATCAGAATTCTGAAGGCACAGGACAAGCAGCAGATCTTAAAAGCACTCAAGCAGCAATCAACCAAATCACCGGGAAACTAAATAGAGTAATCAAGAAAACAAACGAGAAATTCCATCAAATCGAAAAAGAATTCTCAGAAGTAGAAGGAAGAATTCAGGACCTAGAGAAATACGTTGAAGACACTAAAATAGATCTCTGGTCTTACAACGCTGAGATTCTTGTTGCCCTGGAGAACCAACATACAATTGATTTAACCGACTCAGAGATGAGCAAACTGTTCGAAAGAACAAGAAGGCAACTGCGGGAAAATGCTGAGGACATGGGCAATGGTTGCTTCAAAATATACCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCATGATATATACAGAAACGAGGCATTAAACAATCGGTTCCAGATCAAAGGTGTTCAGCTAAAGTCAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGCTTTTTGCTTTGTGTTGTTCTGCTGGGGTTCATTATGTGGGCCTGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA"
	new_viruses_a = []
	for v in viruses:
		dist = distance(reassortant_seq, v['seq'])
		if (dist > 75):
			new_viruses_a.append(v)

	reassortant_seq = "ATGAAGACTATCATTGCTTTTAGCTGCATCTTATGTCAGATCTCCGCTCAAAAACTCCCCGGAAGTGACAACAGCATGGCAACGCTGTGCCTGGGGCATCACGCAGTACCAAACGGAACGTTAGTGAAAACAATAACAGATGACCAAATTGAAGTGACTAATGCTACTGAGCTGGTCCAGAGTACCTCAAAAGGTGAAATATGCAGTAGTCCTCACCAAATCCTTGATGGAAAAAATTGTACACTGATAGATGCTCTATTGGGAGACCCTCATTGTGATGACTTCCAAAACAAGAAATGGGACCTTTTTGTTGAACGAAGCACAGCTTACAGCAACTGTTACCCTTATTATGTGCCGGATTATGCCTCCCTTAGGTCACTAGTTGCCTCATCCGGCACCCTGGAATTTACTCAAGAAAGCTTCAATTGGACTGGGGTTGCTCAAGACGGAGCAAGCTATTCTTGCAGAAGGGAATCTGAAAACAGTTTCTTTAGTAGATTGAATTGGTTATATAGTTTGAATTACAAATATCCAGCGCTGAACGTAACTATGCCAAACAATGACAAATTTGACAAATTGTACATTTGGGGGGTACACCACCCGGGTACGGACAAGGACCAAACCAGTCTATATATTCAAGCATCAGGGAGAGTTACAGTCTCCACCAAATGGAGCCAACAAACTGTAATCCCGAATATCGGGTCTAGACCCTGGATAAGGGGTGTCTCCAGCATAATAAGCATCTATTGGACAATAGTAAAACCGGGAGACATACTTTTGATTAACAGCACAGGGAATCTAATTGCCCCTCGGGGTTACTTCAAAATACAAAGTGGGAAAAGCTCAATAATGAGGTCAGATGCACACATTGGCAACTGCAACTCTGAATGCATTACCCCAAATGGAAGCATTCCCAACGACAAACCTTTTCAAAATGTAAACAGAATAACATATGGGGCCTGTCCCAGATATGTTAAGCAAAACACTCTGAAATTAGCAACAGGAATGCGGAATGTACCAGAGAAACAAACTAGAGGCATATTCGGCGCAATCGCAGGTTTCATAGAAAATGGTTGGGAAGGGATGGTGGACGGTTGGTATGGTTTCAGGCATCAAAACTCTGAAGGCACAGGGCAAGCAGCAGATCTTAAAAGCACTCAAGCGGCAATCAACCAAATCACCGGGAAACTAAATAGAGTAATCAAGAAGACGAATGAAAAATTCCATCAGATCGAAAAAGAATTCTCAGAAGTAGAAGGGAGAATTCAGGACCTAGAGAGATACGTTGAAGACACTAAAATAGACCTCTGGTCTTACAACGCGGAGCTTCTTGTTGCCCTGGAGAACCAACATACAATTGATTTAACTGACTCAGAAATGAACAAACTGTTCGAAAGGACAAGGAAGCAACTGCGGGAAAATGCTGAGGACATGGGCAATGGATGCTTTAAAATATATCACAAATGTGACAATGCCTGCATAGGATCAATCAGAAATGGAACTTATGACCATGATGTATACAGAGACGAAGCAGTAAACAATCGGTTCCAGATCAAAGGTGTTCAGCTGAAGTTAGGATACAAAGATTGGATCCTATGGATTTCCTTTGCCATATCATGCTTTTTGCTTTGTGCTGTTCTGCTAGGATTCATTATGTGGGCATGCCAAAAAGGCAACATTAGGTGCAACATTTGCATTTGA"
	new_viruses_b = []
	for v in new_viruses_a:
		dist = distance(reassortant_seq, v['seq'])
		if (dist > 75):
			new_viruses_b.append(v)

	return new_viruses_b

def main():

	print "--- Clean at " + time.strftime("%H:%M:%S") + " ---"

	viruses = read_json('data/virus_align.json')
	print str(len(viruses)) + " initial viruses"

	# mask extraneous columns and ambiguous bases
	mask_from_outgroup(viruses)
	clean_ambiguous(viruses)

	# clean gapped sequences
	viruses = clean_gaps(viruses)
	print str(len(viruses)) + " with complete HA"

	# clean sequences by distance
	viruses = clean_distances(viruses)
	print str(len(viruses)) + " with clock"

	# clean sequences by outbreak
	viruses = clean_outbreaks(viruses)
	print str(len(viruses)) + " with outbreak sequences removed"

	# clean reassortant sequences
	viruses = clean_reassortants(viruses)
	print str(len(viruses)) + " with triple reassortants removed"

	write_json(viruses, 'data/virus_clean.json')

if __name__ == "__main__":
	main()