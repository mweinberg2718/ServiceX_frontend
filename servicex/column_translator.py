# Copyright (c) 2019, IRIS-HEP
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


class ParticleCollection:
    def __init__(self, collection_name, attributes):
        self.collection_name = collection_name
        self.attributes = attributes


class ColumnTranslator:
    def translate(self, request):
        """
        (call ResultTTree
            (call Select
                (call Select (call EventDataset (list "localds:bogus"))
                (lambda (list e)
                    (list (call (attr e "Electrons") "Electrons")
                          (call (attr e "Muons") "Muons"))))
                          (lambda (list e)
                                (list (call (attr (subscript e 0) "Select")
                                    (lambda (list ele) (call (attr ele "e"))))
                                (call (attr (subscript e 0) "Select")
                                    (lambda (list ele) (call (attr ele "pt"))))
                                (call (attr (subscript e 0) "Select") (lambda (list ele) (call (attr ele "phi")))) (call (attr (subscript e 0) "Select") (lambda (list ele) (call (attr ele "eta")))) (call (attr (subscript e 1) "Select") (lambda (list mu) (call (attr mu "e")))) (call (attr (subscript e 1) "Select") (lambda (list mu) (call (attr mu "pt")))) (call (attr (subscript e 1) "Select") (lambda (list mu) (call (attr mu "phi")))) (call (attr (subscript e 1) "Select") (lambda (list mu) (call (attr mu "eta"))))))) (list "e_E" "e_pt" "e_phi" "e_eta" "mu_E" "mu_pt" "mu_phi" "mu_eta") "forkme" "dude.root")

        :param col_list:
        :return:
        """
        result = "(call ResultTTree (call Select (call Select (call EventDataset (list 'localds:bogus')) (lambda (list e) (list "
        collection_select = ["(call (attr e '%s') '%s')" % (c.collection_name, c.collection_name) for c in request]
        result = result + " ".join(collection_select) + ")"
        print(result)

ex = [
    ParticleCollection("AntiKt4EMTopoJets", [
        'e',
        'eta',
        'index',
        'm',
        'phi',
        'pt',
        'px',
        'py',
        'pz',
        'rapidity'
    ]),
    ParticleCollection("AntiKt4PV0TrackJets", [
        'e',
        'eta',
        'index',
        'm',
        'phi',
        'pt',
        'px',
        'py',
        'pz',
        'rapidity'
    ]),
]

ColumnTranslator().translate(ex)