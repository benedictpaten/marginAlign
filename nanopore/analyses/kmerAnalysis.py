from nanopore.analyses.abstractAnalysis import AbstractAnalysis
from jobTree.src.bioio import fastqRead, fastaRead, system, reverseComplement
from nanopore.analyses.utils import samIterator
import pysam, os, itertools
from collections import Counter
from math import log


class KmerAnalysis(AbstractAnalysis):
    """Runs kmer analysis"""

    def countKmers(self):
        refKmers, readKmers = Counter(), Counter()

        for name, seq in fastaRead(self.referenceFastaFile):
            for i in xrange(self.kmerSize, len(seq)):
                if "N" not in seq[ i - self.kmerSize : i ]:
                    refKmers[ seq[ i - self.kmerSize : i ] ] += 1

        for name, seq, qual in fastqRead(self.readFastqFile):
            for i in xrange(self.kmerSize, len(seq)):
                if "N" not in seq[ i - self.kmerSize : i ]:
                    readKmers[ seq[ i - self.kmerSize : i ] ] += 1

        return (refKmers, readKmers)

    def analyzeCounts(self, refKmers, readKmers, name):
        refSize, readSize = sum(refKmers.values()), sum(readKmers.values())
        outf = open(os.path.join(self.getLocalTempDir(), name + "kmer_counts.txt"), "w")
        outf.write("kmer\trefCount\trefFraction\treadCount\treadFraction\tfoldChange\n")
        
        for kmer in itertools.product("ATGC", repeat=5):
            kmer = "".join(kmer)
            refFraction, readFraction = 1.0 * refKmers[kmer] / refSize, 1.0 * readKmers[kmer] / readSize
            if refFraction != 0:
                foldChange = -log(readFraction / refFraction)
            else:
                foldChange = "-Inf"
            outf.write("\t".join(map(str,[kmer, refKmers[kmer], refFraction, readKmers[kmer], readFraction, foldChange]))+"\n")
        outf.close()
        
        system("Rscript nanopore/analyses/kmer_analysis.R {} {} {}".format(os.path.join(self.getLocalTempDir(), name + "kmer_counts.txt"), os.path.join(self.outputDir, name + "kmer_counts.txt"), os.path.join(self.outputDir, name + "top_bot_sigkmer_counts.txt")))

    def run(self, kmerSize=5):
        AbstractAnalysis.run(self)
        self.kmerSize = kmerSize
        
        #analyze kmers across both files
        refKmers, readKmers = self.countKmers()
        if len(refKmers) > 0 and len(readKmers) > 0:
            self.analyzeCounts(refKmers, readKmers, "all_bases_")
        self.finish()