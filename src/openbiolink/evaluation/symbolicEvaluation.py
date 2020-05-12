from openbiolink import globalConfig as globConf
from openbiolink.evaluation import evalConfig as evalConf
import pandas as pd
import numpy as np

import openbiolink.evaluation.evaluationIO as io
from openbiolink.evaluation.metricTypes import RankMetricType, ThresholdMetricType

from openbiolink.evaluation.metrics import Metrics

import os


class AnyBURLEvaluation:
    def __init__(self, train_path: str = None, test_path: str = None, valid_path: str = None):
        self.evaluation_path = os.path.join(globConf.WORKING_DIR, evalConf.EVAL_OUTPUT_FOLDER_NAME)
        if not os.path.exists(self.evaluation_path):
            os.mkdir(self.evaluation_path)

        if train_path is not None and train_path != "":
            self.training_examples = pd.read_csv(train_path, sep="\t", names=globConf.COL_NAMES_SAMPLES)
            self.training_examples = self.training_examples[globConf.COL_NAMES_TRIPLES]
            self.training_examples.to_csv(os.path.join(self.evaluation_path, "train.txt"), sep="\t", index=False,
                                          header=False)

        if test_path is not None and test_path != "":
            self.test_examples = pd.read_csv(test_path, sep="\t", names=globConf.COL_NAMES_SAMPLES)
            self.test_examples = self.test_examples[globConf.COL_NAMES_TRIPLES]
            self.test_examples.to_csv(os.path.join(self.evaluation_path, "test.txt"), sep="\t", index=False,
                                      header=False)

        if valid_path is not None and valid_path != "":
            self.validation_examples = pd.read_csv(valid_path, sep="\t", names=globConf.COL_NAMES_SAMPLES)
            self.validation_examples = self.validation_examples[globConf.COL_NAMES_TRIPLES]
            self.validation_examples.to_csv(os.path.join(self.evaluation_path, "valid.txt"), sep="\t", index=False,
                                            header=False)

        self.anyburl_path = self.download_anyburl()
        self.irifab_path = self.download_irifab()

    def train(self, learn_config_path: str):
        from subprocess import Popen, PIPE
        process = Popen(
            ["java", "-Xmx12G", "-cp", self.anyburl_path, "de.unima.ki.anyburl.LearnReinforced", learn_config_path],
            stdout=PIPE, stderr=PIPE)
        while True:
            nextline = process.stdout.readline().decode("utf-8")
            if nextline == '' and process.poll() is not None:
                break
            elif nextline != '':
                print(nextline, end='')
        while True:
            nextline = process.stderr.readline().decode("utf-8")
            if nextline == '' and process.poll() is not None:
                break
            elif nextline != '' and nextline != '\r':
                print(nextline, end='')
        process.communicate()

    def apply_rules(self, apply_config_path: str):
        from subprocess import Popen, PIPE
        process = Popen([self.irifab_path, apply_config_path], stdout=PIPE, stderr=PIPE)
        while True:
            nextline = process.stdout.readline().decode("utf-8")
            if nextline == '' and process.poll() is not None:
                break
            elif nextline != '':
                print(nextline, end='')
        while True:
            nextline = process.stderr.readline().decode("utf-8")
            if nextline == '' and process.poll() is not None:
                break
            elif nextline != '' and nextline != '\r':
                print(nextline, end='')
        output = process.communicate()

    def evaluate(self, eval_config_path: str, metrics: list, ks=None):
        if not ks:
            ks = evalConf.DEFAULT_HITS_AT_K
        os.makedirs(os.path.join(globConf.WORKING_DIR, evalConf.EVAL_OUTPUT_FOLDER_NAME), exist_ok=True)

        threshold_metrics = [m for m in ThresholdMetricType]
        num_threshold_metrics = len([x for x in threshold_metrics if x in metrics])
        ranked_metrics = [m for m in RankMetricType]
        num_ranked_metrics = len([x for x in ranked_metrics if x in metrics])

        unfiltered_metrics = [RankMetricType.MRR_UNFILTERED, RankMetricType.HITS_AT_K_UNFILTERED]
        num_ranked_unfiltered_metrics = len([x for x in unfiltered_metrics if x in metrics])
        filtered_options = bool(num_ranked_metrics - num_ranked_unfiltered_metrics)
        unfiltered_options = bool(num_ranked_unfiltered_metrics)
        metrics_results = {}

        prediction_paths = self.get_prediction_paths(eval_config_path)
        for prediction_path in prediction_paths:
            predictions = self.read_prediction(prediction_path)

            if num_ranked_metrics > 0:
                ranked_metrics_results = self.evaluate_ranked_metrics(ks, metrics, predictions)
                metrics_results.update(ranked_metrics_results)

            if num_threshold_metrics > 0:
                threshold_metrics_results = self.evaluate_threshold_metrics(metrics, predictions)
                metrics_results.update(threshold_metrics_results)
            io.write_metric_results(metrics_results)

    @staticmethod
    def get_prediction_paths(eval_config_path: str):
        with open(eval_config_path) as f:
            file_content = '[root]\n' + f.read()

        from configparser import ConfigParser
        config_parser = ConfigParser()
        config_parser.read_string(file_content)

        predictions_path = config_parser["root"]["PATH_PREDICTIONS"]
        if "|" in predictions_path:
            prefix, values, _ = predictions_path.split("|")
            postfixes = values.split(",")
            predictions_path = list()
            for postfix in postfixes:
                predictions_path.append(prefix + postfix)
        else:
            predictions_path = [predictions_path]
        return predictions_path

    @staticmethod
    def read_prediction(prediction_path: str):
        with open(prediction_path) as pred_file:
            file_content = pred_file.readlines()
        file_content = [x.strip() for x in file_content]
        predictions = list()
        for i in range(0, len(file_content), 3):
            triple = file_content[i].split(" ")
            heads = list(filter(None, file_content[i + 1][7:].strip("\t").split("\t")))
            tails = list(filter(None, file_content[i + 2][7:].strip("\t").split("\t")))

            head_nodes = list()
            head_confidences = list()
            for j in range(0, len(heads), 2):
                head_nodes.append(heads[j])
                head_confidences.append(heads[j + 1])

            tail_nodes = list()
            tail_confidences = list()
            for j in range(0, len(tails), 2):
                tail_nodes.append(tails[j])
                tail_confidences.append(tails[j + 1])
            predictions.append(
                Prediction(triple[0], triple[1], triple[2], head_nodes, head_confidences, tail_nodes, tail_confidences))
        return predictions

    @staticmethod
    def evaluate_ranked_metrics(ks, metrics, predictions):

        ranks_head = list()
        ranks_tail = list()
        num_examples = len(predictions)

        for prediction in predictions:
            if prediction.head_rank != float('inf'):
                ranks_head.append(prediction.head_rank)
            if prediction.tail_rank != float('inf'):
                ranks_tail.append(prediction.tail_rank)

        metric_results = {}
        # HITS@K
        if RankMetricType.HITS_AT_K in metrics:
            metric_results[RankMetricType.HITS_AT_K] = Metrics.calculate_hits_at_k(
                ks=ks,
                ranks_corrupted_heads=ranks_head,
                ranks_corrupted_tails=ranks_tail,
                num_examples=num_examples,
            )
        # HITS@K unfiltered
        if RankMetricType.HITS_AT_K_UNFILTERED in metrics:
            metric_results[RankMetricType.HITS_AT_K_UNFILTERED] = Metrics.calculate_hits_at_k(
                ks=ks,
                ranks_corrupted_heads=ranks_head,
                ranks_corrupted_tails=ranks_tail,
                num_examples=num_examples,
            )
        if RankMetricType.HITS_AT_K_REL in metrics:
            results = {}
            for prediction in predictions:
                if prediction.relation not in results.keys():
                    results[prediction.relation] = list()
                results[prediction.relation].append((prediction.head_rank, prediction.tail_rank))

            metric_results[RankMetricType.HITS_AT_K_REL] = dict()
            for relation in results.keys():
                results[relation] = list(zip(*results[relation]))

                metric_results[RankMetricType.HITS_AT_K_REL][relation] = Metrics.calculate_hits_at_k(
                    ks=ks,
                    ranks_corrupted_heads=results[relation][0],
                    ranks_corrupted_tails=results[relation][1],
                    num_examples=len(results[relation][0])
                )
        # MRR
        if RankMetricType.MRR in metrics:
            metric_results[RankMetricType.MRR] = Metrics.calculate_mrr(
                ranks_corrupted_heads=ranks_head,
                ranks_corrupted_tails=ranks_tail,
                num_examples=num_examples,
            )
        # MRR unfiltered
        if RankMetricType.MRR_UNFILTERED in metrics:
            metric_results[RankMetricType.MRR] = Metrics.calculate_mrr(
                ranks_corrupted_heads=ranks_head,
                ranks_corrupted_tails=ranks_tail,
                num_examples=num_examples,
            )
        return metric_results

    @staticmethod
    def evaluate_threshold_metrics(metrics, predictions):

        scores = list()
        labels = list()

        for prediction in predictions:
            labels = labels + prediction.head_labels
            scores = scores + prediction.head_confidences
            labels = labels + prediction.tail_labels
            scores = scores + prediction.tail_confidences

        metric_results = {}
        # ROC Curve
        if ThresholdMetricType.ROC in metrics:
            fpr, tpr = Metrics.calculate_roc_curve(labels=labels, scores=scores)
            metric_results[ThresholdMetricType.ROC] = (fpr, tpr)
        # Precision Recall Curve
        if ThresholdMetricType.PR_REC_CURVE in metrics:
            pr, rec = Metrics.calculate_pr_curve(labels, scores)
            metric_results[ThresholdMetricType.PR_REC_CURVE] = (pr, rec)
        # ROC AUC
        if ThresholdMetricType.ROC_AUC:
            if ThresholdMetricType.ROC in metric_results.keys():
                fpr, tpr = metric_results[ThresholdMetricType.ROC]
            else:
                fpr, tpr = Metrics.calculate_roc_curve(labels=labels, scores=scores)
                # todo ? auch unique?
            roc_auc = Metrics.calculate_auc(fpr, tpr)
            metric_results[ThresholdMetricType.ROC_AUC] = roc_auc
        # Precision Recall AUC
        if ThresholdMetricType.PR_AUC:
            if ThresholdMetricType.PR_AUC in metric_results.keys():
                pr, rec = metric_results[ThresholdMetricType.PR_REC_CURVE]
            else:
                pr, rec = Metrics.calculate_pr_curve(labels=labels, scores=scores)
                pr = np.asarray(pr)
                rec = np.asarray(rec)
            _, indices = np.unique(pr, return_index=True)
            pr_unique = pr[indices]
            rec_unique = rec[indices]
            pr_auc = Metrics.calculate_auc(pr_unique, rec_unique)
            metric_results[ThresholdMetricType.PR_AUC] = pr_auc
        return metric_results

    def download_anyburl(self):
        anyburl_path = os.path.join(self.evaluation_path, "AnyBURL-RE.jar")
        if not os.path.exists(os.path.join(self.evaluation_path, "AnyBURL-RE.jar")):
            import wget
            wget.download("http://web.informatik.uni-mannheim.de/AnyBURL/AnyBURL-RE.jar",
                          os.path.join(self.evaluation_path, "AnyBURL-RE.jar"))
        return anyburl_path

    def download_irifab(self):
        import platform
        os_name = platform.system()
        if os_name == "Linux":
            irifab_name = "IRIFAB"
        elif os_name == "Windows":
            irifab_name = "IRIFAB.exe"
        else:
            print("OS not supported with IRIFAB")
            import sys
            sys.exit()

        irifab_path = os.path.join(self.evaluation_path, irifab_name)
        if not os.path.exists(irifab_path):
            import wget
            irifab_url = "https://github.com/OpenBioLink/IRIFAB/raw/master/resources/binaries/" + irifab_name
            wget.download(irifab_url, irifab_path)
        return irifab_path


class Prediction:

    def __init__(self, head, relation, tail, head_predictions, head_confidences, tail_predictions, tail_confidences):
        self.head = head
        self.relation = relation
        self.tail = tail

        self.head_predictions = head_predictions
        self.head_confidences = list(map(float, head_confidences))
        self.head_rank, self.head_labels = self.calc_rank_and_labels(head, head_predictions)

        self.tail_predictions = tail_predictions
        self.tail_confidences = list(map(float, tail_confidences))
        self.tail_rank, self.tail_labels = self.calc_rank_and_labels(tail, tail_predictions)

    @staticmethod
    def calc_rank_and_labels(true: str, predictions: list):
        labels = [0 for i in range(len(predictions))]
        for i in range(len(predictions)):
            if predictions[i] == true:
                labels[i] = 1
                return i + 1, labels
        return float('inf'), labels
