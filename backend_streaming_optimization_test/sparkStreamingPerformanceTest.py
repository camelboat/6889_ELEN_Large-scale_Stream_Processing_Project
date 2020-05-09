from pyspark import SparkConf, SparkContext
import re


def hashtagExtractOptimized(words):
    def singleClear(word):
        tagsPool = ["#covid19", "#covid", "#coronavirus", "#covid-19", "#covid_19", "#covidー19", "#covid2019",
                    "covid19-virus", "#covid__19"]
        punctuationPool = [",", ".", "!", "?", ":", "-", ")"]
        if word.lower() in tagsPool:
            return "#covid19"
        elif word[len(word)-1] in punctuationPool:
            return word[0:len(word)-1]
        else:
            return word

    def is_valid(word):
        flag = True
        invalid_word_pool = ["#breaking", "#watch"]
        if "…" in word: flag = False
        if "@" in word: flag = False
        if word[len(word)-2:len(word)].lower() == "rt": flag = False
        if len(word) <= 1: flag = False
        if word.lower() in  invalid_word_pool: flag = False
        return flag

    # words = words.map(lambda word: word.lower())
    pattern = re.compile("#")
    hashtags = words.filter(lambda word: pattern.match(word, 0)) \
                    .filter(lambda word: is_valid(word)) \
                    .map(lambda word: singleClear(word)) \
                    .map(lambda word: (word, 1)) \
                    .reduceByKey(lambda x, y: x + y) \
                    .map(lambda word: (word[1], word[0])) \
                    .sortByKey(ascending=True)
    return hashtags


def hashtagExtractNotOptimized(words):
    def combineSimilarTags(word):
        tagsPool = ["#covid19", "#covid", "#coronavirus", "#covid-19", "#covid_19", "#covidー19", "#covid2019",
                    "covid19-virus", "#covid__19"]
        if word.lower() in tagsPool:
            return "#covid19"
        else:
            return word

    def removeLastPunctuation(word):
        punctuationPool = [",", ".", "!", "?",":","-",")"]
        if word[len(word)-1] in punctuationPool:
            return word[0:len(word)-1]
        else:
            return word

    invalid_word_pool = ["#breaking", "#watch"]
    # words = words.map(lambda word: word.lower())
    pattern = re.compile("#")
    hashtags = words.filter(lambda word: not "…" in word)
    hashtags2 = hashtags.filter(lambda word: not "@" in word)
    hashtags3 = hashtags2.filter(lambda word: not word[len(word)-1:len(word)].lower() == "rt")\
                    .filter(lambda word: len(word) > 1)\
                    .filter(lambda word: not word in invalid_word_pool) \
                    .filter(lambda word: pattern.match(word, 0))


    validHashtags = hashtags3.map(lambda word: removeLastPunctuation(word)) \
                    .map(lambda word: combineSimilarTags(word))

    hashtagsTotalSorted = validHashtags.map(lambda word: (word, 1)) \
                                  .reduceByKey(lambda x, y: x+y) \
                                  .map(lambda word: (word[1], word[0])) \
                                  .sortByKey(ascending=True)
    return hashtagsTotalSorted


def main():
    sc = SparkContext.getOrCreate()
    data = sc.textFile("textfiles/raw-0.txt")
    words = data.flatMap(lambda line: line.split(" "))
    hashtagsTotalSorted = hashtagExtractOptimized(words)
    # hashtagsTotalSorted = hashtagExtractNotOptimized(words)
    print(hashtagsTotalSorted.top(10))


if __name__ == "__main__":
    main()